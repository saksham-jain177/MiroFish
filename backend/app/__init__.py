"""
Synthetica Cognitive Sandbox — Flask Backend
"""

import os
import warnings

warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request, send_from_directory, redirect
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    logger = setup_logger('synthetica')
    
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("Synthetica Cognitive Sandbox — Backend Starting...")
        logger.info("=" * 50)
    
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("")
    
    @app.before_request
    def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f": {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f": {request.get_json(silent=True)}")
    
    @app.after_request
    def log_response(response):
        logger = get_logger('mirofish.request')
        logger.debug(f": {response.status_code}")
        return response
    
    # Legacy Microfish endpoints disabled to prevent broken module imports
    # from .api import graph_bp, simulation_bp, report_bp
    from .api.replay import replay_bp
    # app.register_blueprint(graph_bp, url_prefix='/api/graph')
    # app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    # app.register_blueprint(report_bp, url_prefix='/api/report')
    app.register_blueprint(replay_bp, url_prefix='/api/replay')
    
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'Synthetica Cognitive Sandbox'}
        
    @app.route('/')
    def index():
        return redirect('/observatory')
    
    @app.route('/observatory')
    def observatory():
        """Serve the Neural Observatory dashboard."""
        return send_from_directory(
            app.static_folder or 'static',
            'replay.html'
        )
    
    if should_log_startup:
        logger.info("Synthetica Backend Ready.")
    
    return app

