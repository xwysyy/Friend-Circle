from app.core import collect_from_config, load_config

import json
import logging
import os

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
log_file = os.path.join(RESULTS_DIR, "grab.log")
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

config = load_config(os.path.join("config", "conf.yaml"))
if config["spider_settings"]["enable"]:
    logging.info("爬虫已启用")
    result, lost_friends = collect_from_config(config)
    with open(os.path.join(RESULTS_DIR, "all.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(os.path.join(RESULTS_DIR, "errors.json"), "w", encoding="utf-8") as f:
        json.dump(lost_friends, f, ensure_ascii=False, indent=2)
    logging.info("抓取与写入完成：all.json, errors.json")
