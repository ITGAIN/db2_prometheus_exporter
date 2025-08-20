# DB2 Prometheus Exporter

A customizable **Prometheus Exporter** for **IBM Db2**, designed to run multiple SQL queries across multiple databases and expose the results as metrics for monitoring purposes. Docker Compose comes with prometheus and grafana for testing purposes. 

## 🚀 Features

- ✅ Supports multiple Db2 database instances
- ✅ Flexible query configuration using a YAML file
- ✅ Handles both **gauge** and **counter** metrics
- ✅ Dynamic labels per query (e.g. for database, host, tenant, etc.)
- ✅ Graceful reconnect handling if a database becomes temporarily unavailable
- ✅ `/metrics` endpoint returns all data; optional sub-endpoints per query
- ✅ Dockerized setup with Prometheus and Grafana included
- ✅ Predefined Grafana dashboards (optional)

---

## 📁 Project Structure
```
.
├── config.yaml          # Query and DB config
├── exporter.py          # Prometheus exporter logic
├── docker-compose.yml   # Full setup: exporter, Prometheus, Grafana
└── dashboards/          # Prebuilt Grafana dashboards (optional)
```
---

## ⚙️ Configuration

### `config.yaml`

```yaml
exporter_port: 8000

databases:
  - host: db2-host1
    port: 50000
    database: SAMPLE
    user: db2inst1
    password: secret

queries:
  - metric_origin: mon_get_database
    query: "SELECT * FROM TABLE(MON_GET_DATABASE(-2))"
    extra_labels: ["MEMBER"]
    gauge_metrics: []  # Fill in as needed

	# metric_origin: Used as a label to identify the source query
	# gauge_metrics: List of metric names that are gauges (all others assumed to be counters)
	# extra_labels: Column names from the query to be used as additional labels
```


## 🐳 Docker Compose

```
docker-compose up --build
```

Includes:
* DB2 exporter
* Prometheus (with pre-configured scrape targets)
* Grafana (with Prometheus datasource)


## 🔍 Prometheus Configuration

Prometheus scrapes metrics from the exporter:

scrape_configs:
  - job_name: 'db2'
    scrape_interval: 15s
    static_configs:
      - targets: ['exporter:8000']

  - job_name: 'db2-mon'
    scrape_interval: 5s
    metrics_path: /metrics/mongetdatabase
    static_configs:
      - targets: ['exporter:8000']


## 📊 Grafana

Grafana is included and runs on http://localhost:3000
* Default user: admin
* Default password: admin
* Prometheus datasource is pre-configured
* Optional: Import dashboards from the dashboards/ folder

## 🔁 Reconnection Handling

The exporter automatically tries to reconnect to any database that becomes unavailable, using a background thread. If a query fails due to a lost connection, the exporter marks the connection as dead and reconnects it later.


## 🧪 Sample Prometheus Query

rate(db2_mongetdatabase_log_write_time_total[5m])

This gives you the rate of log write time (ms) over 5 minutes.


## 📝 License

This project is licensed under the **Business Source License 1.1 (BSL 1.1)**.

- ✅ Free for non-commercial, evaluation, and development purposes  
- ❌ Commercial and production use requires a paid license  
- 📆 The code will be re-licensed under the **Apache License 2.0** on **January 1, 2100**

See the [LICENSE.txt](./LICENSE.txt) file for full details.

To obtain a commercial license, please contact: **[your-email@example.com]**

## 🤝 Contributing

Contributions are welcome for testing, bug reports, and general improvements within the allowed use case.  
Please **do not use this software in production** without a commercial license.