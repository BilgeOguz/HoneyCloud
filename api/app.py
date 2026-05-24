import os
import logging
from flask import Flask, request, jsonify
from flask_caching import Cache
from models import db, Alert
from prometheus_flask_exporter import PrometheusMetrics
import json
from pythonjsonlogger import jsonlogger

# Replaced
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[handler])

#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#logger = logging.getLogger(__name__)

cache = Cache()

def create_app():
    app = Flask(__name__)

    database_url = os.environ.get('DATABASE_URL', 'sqlite:///:memory:')
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['CACHE_TYPE'] = 'RedisCache'
    app.config['CACHE_REDIS_URL'] = redis_url
    app.config['CACHE_DEFAULT_TIMEOUT'] = 60

    db.init_app(app)
    cache.init_app(app)
    metrics = PrometheusMetrics(app)
    metrics.info('honeymanager_info', 'HoneyManager API', version='1.0.0')

    @app.route('/api/health', methods=['GET'])
    def health_check():
        try:
            db.session.execute(db.text('SELECT 1'))
            return jsonify({'status': 'healthy', 'database': 'connected'}), 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({'status': 'unhealthy', 'error': str(e)}), 503

    @app.route('/api/logs', methods=['POST'])
    def receive_log():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON payload'}), 400

        required_fields = ['severity', 'honeypot_name', 'source_ip', 'event_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400

        try:
            new_alert = Alert(
                severity=data['severity'],
                honeypot_name=data['honeypot_name'],
                honeypot_type=data.get('honeypot_type'),
                source_ip=data['source_ip'],
                event_type=data['event_type'],
                description=data.get('description'),
                raw_data=data.get('raw_data')
            )
            db.session.add(new_alert)
            db.session.commit()
            cache.delete('recent_logs')  # invalidate cache on new log
            logger.info(f"New log from {data['source_ip']} - {data['event_type']}")
            return jsonify({'success': True, 'alert_id': new_alert.id}), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save log: {e}")
            return jsonify({'success': False, 'error': 'Database error'}), 500

    @app.route('/api/logs', methods=['GET'])
    @cache.cached(timeout=60, key_prefix='recent_logs')  # cache this for 60 seconds
    def get_logs():
        try:
            limit = request.args.get('limit', 10, type=int)
            alerts = Alert.query.order_by(Alert.timestamp.desc()).limit(limit).all()
            return jsonify({'success': True, 'logs': [a.to_dict() for a in alerts]}), 200
        except Exception as e:
            return jsonify({'success': False, 'error': 'Database error'}), 500

    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
