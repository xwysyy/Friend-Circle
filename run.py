from friend_circle.get_info import fetch_and_process_data, sort_articles_by_time
from friend_circle.get_conf import load_config

import json
import logging

# 配置日志
log_file = "grab.log"
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 爬虫部分内容
config = load_config("./conf.yaml")
if config["spider_settings"]["enable"]:
    logging.info("爬虫已启用")
    json_url = config['spider_settings']['json_url']
    article_count = config['spider_settings']['article_count']
    max_workers = int(config['spider_settings'].get('max_workers', 10))
    force_ipv4 = bool(config['spider_settings'].get('force_ipv4', False))
    logging.info("正在从 %s 获取，每个博客获取 %d 篇文章，并发 %d (IPv4-only=%s)", json_url, article_count, max_workers, force_ipv4)
    result, lost_friends = fetch_and_process_data(
        json_url=json_url,
        count=article_count,
        max_workers=max_workers,
        force_ipv4=force_ipv4,
    )
    sorted_result = sort_articles_by_time(result)
    with open("all.json", "w", encoding="utf-8") as f:
        json.dump(sorted_result, f, ensure_ascii=False, indent=2)
    with open("errors.json", "w", encoding="utf-8") as f:
        json.dump(lost_friends, f, ensure_ascii=False, indent=2)
    logging.info("抓取与写入完成：all.json, errors.json")
