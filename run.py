from app.core import collect_from_config, fetch_ignore_ids, load_config

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

    spider_settings = config.get("spider_settings", {}) or {}
    ignore_url = os.getenv("FRIEND_CIRCLE_IGNORE_URL") or spider_settings.get("ignore_url", "")
    ignore_ids = fetch_ignore_ids(ignore_url)

    if ignore_ids:
        logging.info(f"已加载忽略列表，共 {len(ignore_ids)} 条，将生成 all.personal.json")
        personal_result, personal_lost = collect_from_config(config, ignore_ids=ignore_ids)
    else:
        logging.info("忽略列表为空（或不可用），all.personal.json 将与 all.json 相同")
        personal_result, personal_lost = result, lost_friends

    with open(os.path.join(RESULTS_DIR, "all.personal.json"), "w", encoding="utf-8") as f:
        json.dump(personal_result, f, ensure_ascii=False, indent=2)
    with open(os.path.join(RESULTS_DIR, "errors.personal.json"), "w", encoding="utf-8") as f:
        json.dump(personal_lost, f, ensure_ascii=False, indent=2)
    logging.info("抓取与写入完成：all.personal.json, errors.personal.json")
