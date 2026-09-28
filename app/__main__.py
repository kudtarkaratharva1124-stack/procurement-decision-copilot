from .app import app
from .config import settings
app.run(host=settings.host, port=settings.port, debug=False)
