from flask import Blueprint, jsonify, current_app
import os
import json

replay_bp = Blueprint('replay', __name__)

@replay_bp.route('/list', methods=['GET'])
def list_runs():
    """Lists all available .jsonl batch simulation logs."""
    sim_dir = current_app.config.get('OASIS_SIMULATION_DATA_DIR', './uploads/simulations')
    runs = []
    
    if not os.path.exists(sim_dir):
        return jsonify({"runs": []})
        
    for root, _, files in os.walk(sim_dir):
        for f in files:
            if f.endswith('.jsonl'):
                abs_path = os.path.join(root, f)
                rel_path = os.path.relpath(abs_path, sim_dir).replace('\\', '/')
                try:
                    runs.append((rel_path, os.path.getmtime(abs_path)))
                except OSError:
                    pass  # File was deleted or locked mid-scan
                
    # Sort strictly by modified time, newest first
    runs.sort(key=lambda x: x[1], reverse=True)
    return jsonify({"runs": [r[0] for r in runs]})

@replay_bp.route('/clear', methods=['POST'])
def clear_runs():
    """Wipes all simulation logs from the disk to clean the UI archive."""
    import shutil
    sim_dir = current_app.config.get('OASIS_SIMULATION_DATA_DIR', './uploads/simulations')
    if os.path.exists(sim_dir):
        for item in os.listdir(sim_dir):
            item_path = os.path.join(sim_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, ignore_errors=True)
            else:
                try:
                    os.remove(item_path)
                except OSError:
                    pass
    return jsonify({"status": "cleared"})

@replay_bp.route('/load/<path:filename>', methods=['GET'])
def load_run(filename):
    """Loads a specific run trajectory."""
    sim_dir = current_app.config.get('OASIS_SIMULATION_DATA_DIR', './uploads/simulations')
    filepath = os.path.join(sim_dir, filename)
    
    if not os.path.normpath(filepath).startswith(os.path.normpath(sim_dir)):
        return jsonify({"error": "Invalid path"}), 400
        
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    trajectory = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                trajectory.append(json.loads(line))
                
    return jsonify({"trajectory": trajectory})
