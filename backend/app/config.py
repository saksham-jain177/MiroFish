"""

 .env 
"""

import os
from dotenv import load_dotenv

project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    load_dotenv(override=True)


class Config:
    """Flask"""
    
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    JSON_AS_ASCII = False
    
    LLM_API_KEY = os.environ.get('LLM_API_KEY', 'ollama')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'http://localhost:11434/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'llama3.1:8b-instruct-q4_K_M')
    
    SYNTHETICA_BATCH_SIZE = int(os.environ.get('SYNTHETICA_BATCH_SIZE', '1'))
    SYNTHETICA_MAX_CONTEXT = int(os.environ.get('SYNTHETICA_MAX_CONTEXT', '4096'))
    
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY', 'zep_local')
    
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_CHUNK_OVERLAP = 50
    
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))
    
    # Phase 2 Contextual Scoring Weights (Configurable priors)
    SCORING = {
        'desperation_mitigation': float(os.environ.get('SYNTH_SCORE_DESP', '-0.15')),
        'trust_abuse_bonus': float(os.environ.get('SYNTH_SCORE_ABUSE', '0.20')),
        'repeat_offender_bonus': float(os.environ.get('SYNTH_SCORE_REPEAT', '0.20')),
        'altruism_discount': float(os.environ.get('SYNTH_SCORE_ALTRUISM', '-0.15'))
    }
    
    # Pre-registered Base Action Determinist Scores
    BASE_CCS_MAP = {
        "GATHER_LOCAL": 0.0,
        "COOPERATE": 0.0,
        "DECEIVE": 0.1,
        "GATHER_BORDER": 0.2,
        "STEAL_RESOURCE": 0.4,
        "SABOTAGE": 0.6,
        "CROSS_BARRIER": 1.0
    }
    
    @classmethod
    def validate(cls):
        """"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY ")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY ")
        return errors

