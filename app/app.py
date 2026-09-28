from __future__ import annotations
import threading, time
from flask import Flask, jsonify, render_template, request
from .config import settings
from .models import init_db, SessionLocal, AuditLog, Case
from .connectors.graph_api import GraphClient
from .services.cases import CaseService
from .connectors.local_discovery import discover_local
from .connectors.local_outlook import LocalOutlookClient
from .services.rfa_knowledge import RFAKnowledgeService

init_db()
app=Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key=settings.secret_key
service=CaseService()

def scheduler():
    while True:
        try: service.ingest()
        except Exception as e: app.logger.exception('Scheduled ingestion failed: %s', e)
        time.sleep(max(60,settings.schedule_interval_minutes*60))
if settings.app_env != 'test': threading.Thread(target=scheduler,daemon=True).start()

@app.get('/')
def index(): return render_template('index.html')
@app.get('/api/rfa-knowledge')
def rfa_knowledge():
    docs=RFAKnowledgeService().all()
    return jsonify({'count':len(docs),'documents':[{'name':d['name'],'category':d['category']} for d in docs]})

@app.get('/api/health')
def health():
    azure_ok = bool(
        settings.azure_openai_endpoint
        and settings.azure_openai_api_key
        and settings.azure_openai_deployment
    )

    graph_ok = service.context.graph is not None

    return jsonify({
        'status': 'ok',
        'environment': settings.app_env,
        'demo_mode': settings.demo_mode,
        'azure_openai_configured': azure_ok,
        'graph_configured': graph_ok
    })


@app.get('/api/discover')
def discover():
    result = discover_local()

    graph_ok = service.context.graph is not None

    if graph_ok:
        result['mailbox_source'] = 'microsoft_graph'
    elif result.get('outlook', {}).get('installed'):
        result['mailbox_source'] = 'local_outlook'
    else:
        result['mailbox_source'] = 'none'

    result['azure_openai_configured'] = bool(
        settings.azure_openai_endpoint
        and settings.azure_openai_api_key
        and settings.azure_openai_deployment
    )

    result['graph_configured'] = graph_ok
    result['scheduler_interval_minutes'] = settings.schedule_interval_minutes

    return jsonify(result)
@app.post('/api/refresh')
def refresh():
    return jsonify({'ingested':service.ingest()})
@app.get('/api/cases')
def cases(): return jsonify(service.list())
@app.get('/api/cases/<case_key>')
def case(case_key):
    c=service.get(case_key)
    return (jsonify(c),200) if c else (jsonify({'error':'not found'}),404)
@app.post('/api/cases/<case_key>/analyze')
def analyze(case_key):
    try:return jsonify(service.process(case_key))
    except KeyError:return jsonify({'error':'case not found'}),404
    except Exception as e:return jsonify({'error':str(e)}),500
@app.post('/api/cases/<case_key>/decision')
def decision(case_key):
    body=request.get_json(silent=True) or {}
    try:return jsonify(service.decide(case_key,body.get('decision',''),body.get('note',''),body.get('edited_draft','')))
    except KeyError:return jsonify({'error':'case not found'}),404
    except Exception as e:return jsonify({'error':str(e)}),400

@app.post('/api/cases/<case_key>/outlook-draft')
def outlook_draft(case_key):
    body=request.get_json(silent=True) or {}
    try:
        return jsonify(service.save_outlook_draft(case_key, body.get('html','')))
    except KeyError:return jsonify({'error':'case not found'}),404
    except Exception as e:return jsonify({'error':str(e)}),500

@app.get('/api/audit/<case_key>')
def audit(case_key):
    from sqlalchemy import select
    with SessionLocal() as db:
        rows=db.scalars(select(AuditLog).where(AuditLog.case_key==case_key).order_by(AuditLog.created_at.asc())).all()
        return jsonify([{'event_type':r.event_type,'actor':r.actor,'payload':r.payload,'created_at':r.created_at.isoformat()} for r in rows])

@app.post('/api/automation/run')
def automation_run():
    try:
        ingested = service.ingest()

        analyzed = 0
        failed = 0
        skipped = 0

        for case in service.list():

            # Do not automatically re-process completed human decisions.
            if case.get('status') in {
                'approved',
                'rejected',
                'revision_requested'
            }:
                skipped += 1
                continue

            # Already analyzed cases do not need to be analyzed again.
            if case.get('recommendation'):
                skipped += 1
                continue

            try:
                service.process(case['case_key'])
                analyzed += 1

            except Exception as exc:
                failed += 1
                print(
                    f"Automation analysis failed for "
                    f"{case['case_key']}: {exc}"
                )

        return jsonify({
            'status': 'ok',
            'ingested': ingested,
            'analyzed': analyzed,
            'failed': failed,
            'skipped': skipped
        })

    except Exception as exc:
        return jsonify({
            'status': 'error',
            'error': str(exc)
        }), 500

if __name__=='__main__': app.run(host=settings.host,port=settings.port,debug=settings.app_env=='development')
