from flask import Flask, Response
import ibm_db
import yaml
import logging
from prometheus_client import generate_latest, CollectorRegistry
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
import threading
import time

app = Flask(__name__)

# --- Logging setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Load config ---
with open("config.yaml") as f:
    config = yaml.safe_load(f)

query_configs = config["queries"]
db_instances = config["databases"]

# --- Connection handling ---
db_conns = {}  # {key: {"conn": ..., "info": ..., "lock": ...}}

def connect_to_db(db):
    dsn = f"DATABASE={db['database']};HOSTNAME={db['host']};PORT={db['port']};PROTOCOL=TCPIP;UID={db['user']};PWD={db['password']};"
    try:
        conn = ibm_db.connect(dsn, "", "")
        logger.info(f"Connected to DB: {db['host']}:{db['port']}/{db['database']}")
        return conn
    except Exception as e:
        logger.warning(f"Failed to connect to {db['host']}:{db['port']}/{db['database']}: {e}")
        return None

def init_connections():
    for db in db_instances:
        key = (db['host'], db['port'], db['database'])
        conn = connect_to_db(db)
        db_conns[key] = {
            "conn": conn,
            "info": db,
            "lock": threading.Lock()
        }

def reconnect_loop():
    while True:
        for key, db in db_conns.items():
            if db["conn"] is None:
                logger.info(f"Reconnecting to DB: {key}")
                conn = connect_to_db(db["info"])
                with db["lock"]:
                    db["conn"] = conn
        time.sleep(30)

init_connections()
threading.Thread(target=reconnect_loop, daemon=True).start()

# --- Collector ---
class DB2Collector:
    def __init__(self, db_conns, query_configs):
        self.db_conns = db_conns
        self.query_configs = query_configs

    def collect(self):
        for key, db in self.db_conns.items():
            db_info = db["info"]
            with db["lock"]:
                conn = db["conn"]

            if not conn:
                logger.debug(f"Skipping DB {key} due to missing connection.")
                continue

            for query_config in self.query_configs:
                yield from self.run_query(conn, db_info, query_config)

    def run_query(self, conn, db_info, query_config):
        try:
            cursor = ibm_db.exec_immediate(conn, query_config["query"])
            row = ibm_db.fetch_assoc(cursor)
            while row != False:
                if not row:
                    cursor.close()
                    return

                origin = query_config.get("metric_origin", "unknown").lower()
                labels = {
                    "host": db_info["host"],
                    "port": str(db_info["port"]),
                    "database": db_info["database"],
                }

                for lbl in query_config.get("extra_labels", []):
                    val = row.get(lbl.upper())
                    if val is not None:
                        labels[lbl] = str(val)
                    else:
                        return

                label_keys = sorted(labels.keys())
                label_values = [labels[k] for k in label_keys]

                for col, val in row.items():
                    if not isinstance(val, (int, float)):
                        continue

                    metric_name = f"db2_{origin}_{col.lower()}"
                    is_gauge = col in query_config.get("gauge_metrics", [])
                    metric_cls = GaugeMetricFamily if is_gauge else CounterMetricFamily

                    metric = metric_cls(
                        metric_name,
                        f"DB2 {'gauge' if is_gauge else 'counter'} for {col}",
                        labels=label_keys
                    )
                    metric.add_metric(label_values, val)
                    yield metric
                row = ibm_db.fetch_assoc(cursor)

        except Exception as e:
            logger.warning(f"Error running query for {db_info['database']}: {e}")
            # If connection error: mark connection as dead
            if "SQLSTATE=08003" in str(e) or "Connection is closed" in str(e):
                key = (db_info["host"], db_info["port"], db_info["database"])
                with self.db_conns[key]["lock"]:
                    self.db_conns[key]["conn"] = None
                    logger.info(f"Marked DB connection as dead for: {key}")

# --- Flask endpoints ---
@app.route("/metrics/<origin>")
def metrics_origin(origin):
    registry = CollectorRegistry()
    matched_queries = [q for q in query_configs if q.get("metric_origin") == origin]
    if not matched_queries:
        return Response(f"No queries found for origin: {origin}", status=404)

    registry.register(DB2Collector(db_conns, matched_queries))
    return Response(generate_latest(registry), mimetype="text/plain")

@app.route("/metrics")
def metrics_all():
    registry = CollectorRegistry()
    registry.register(DB2Collector(db_conns, query_configs))
    return Response(generate_latest(registry), mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.get("exporter_port", 8000))