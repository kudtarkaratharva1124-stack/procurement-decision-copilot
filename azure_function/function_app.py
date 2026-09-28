import os
import logging
import urllib.request

import azure.functions as func


app = func.FunctionApp()


@app.timer_trigger(
    schedule="%TIMER_SCHEDULE%",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True
)
def procurement_poll(timer: func.TimerRequest) -> None:

    logging.info("Procurement polling trigger started.")

    backend_url = os.getenv(
        "BACKEND_URL",
        "http://127.0.0.1:8000"
    )

    endpoint = (
        backend_url.rstrip("/")
        + "/api/automation/run"
    )

    try:

        request = urllib.request.Request(
            endpoint,
            method="POST",
            headers={
                "Content-Type": "application/json"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=120
        ) as response:

            body = response.read().decode("utf-8")

            logging.info(
                "Automation response: %s",
                body
            )

    except Exception as exc:

        logging.exception(
            "Procurement polling failed: %s",
            exc
        )
