package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/xwysyy/Friend-Circle/scraper"
)

const (
	configPath = "config/conf.yaml"
	resultsDir = "results"
)

func main() {
	// Ensure results directory exists
	if err := os.MkdirAll(resultsDir, 0o755); err != nil {
		log.Fatalf("创建 results 目录失败: %v", err)
	}

	// Setup logging to file
	logFile, err := os.OpenFile(
		filepath.Join(resultsDir, "grab.log"),
		os.O_CREATE|os.O_WRONLY|os.O_TRUNC,
		0o644,
	)
	if err != nil {
		log.Fatalf("打开日志文件失败: %v", err)
	}
	defer logFile.Close()
	log.SetOutput(logFile)
	log.SetFlags(log.Ldate | log.Ltime)

	// Load configuration
	cfg, err := scraper.LoadConfig(configPath)
	if err != nil {
		log.Fatalf("加载配置失败: %v", err)
	}

	if !cfg.SpiderSettings.Enable {
		log.Println("爬虫未启用，退出")
		return
	}

	log.Println("爬虫已启用")

	client := scraper.NewHTTPClient()

	// --- First pass: all.json + errors.json ---
	result, errorEntries := collectFromConfig(cfg, client, nil)

	writeJSON(filepath.Join(resultsDir, "all.json"), result)
	writeJSON(filepath.Join(resultsDir, "errors.json"), errorEntries)
	log.Println("抓取与写入完成：all.json, errors.json")

	// --- Second pass: personal (with ignore list) ---
	ignoreURL := os.Getenv("FRIEND_CIRCLE_IGNORE_URL")
	if ignoreURL == "" {
		ignoreURL = cfg.SpiderSettings.IgnoreURL
	}
	ignoreIDs := scraper.FetchIgnoreIDs(ignoreURL, client)

	if len(ignoreIDs) > 0 {
		log.Printf("已加载忽略列表，共 %d 条，将生成 all.personal.json", len(ignoreIDs))
		personalResult, personalErrors := collectFromConfig(cfg, client, ignoreIDs)
		writeJSON(filepath.Join(resultsDir, "all.personal.json"), personalResult)
		writeJSON(filepath.Join(resultsDir, "errors.personal.json"), personalErrors)
	} else {
		log.Println("忽略列表为空（或不可用），all.personal.json 将与 all.json 相同")
		writeJSON(filepath.Join(resultsDir, "all.personal.json"), result)
		writeJSON(filepath.Join(resultsDir, "errors.personal.json"), errorEntries)
	}
	log.Println("抓取与写入完成：all.personal.json, errors.personal.json")
}

// collectFromConfig orchestrates the scraping across all JSON sources.
func collectFromConfig(
	cfg *scraper.Config,
	client *http.Client,
	ignoreIDs map[string]struct{},
) (*scraper.Result, [][]string) {
	spider := cfg.SpiderSettings
	sources := scraper.DiscoverJSONSources(spider.JSONURL)

	aggregated := &scraper.Result{
		ArticleData: []scraper.Article{},
	}
	var allErrors [][]string

	for _, src := range sources {
		log.Printf("开始处理数据源：%s（分类：%s）", src.Path, src.Category)

		friends, err := scraper.LoadFriends(src.Path, client)
		if err != nil {
			log.Printf("无法获取友链 JSON：%s，错误：%v", src.Path, err)
			continue
		}

		result, errEntries := scraper.FetchAndProcessAll(
			client,
			friends,
			spider.ArticleCount,
			spider.MaxWorkers,
			ignoreIDs,
		)

		// Inject category
		for i := range result.ArticleData {
			result.ArticleData[i].Category = src.Category
		}

		// Aggregate statistics
		aggregated.StatisticalData.FriendsNum += result.StatisticalData.FriendsNum
		aggregated.StatisticalData.ActiveNum += result.StatisticalData.ActiveNum
		aggregated.StatisticalData.ErrorNum += result.StatisticalData.ErrorNum
		aggregated.StatisticalData.ArticleNum += result.StatisticalData.ArticleNum
		aggregated.ArticleData = append(aggregated.ArticleData, result.ArticleData...)
		allErrors = append(allErrors, errEntries...)
	}

	// Update timestamp
	aggregated.StatisticalData.LastUpdatedTime = time.Now().Format("2006-01-02 15:04:05")

	// Apply link rewrites
	if len(spider.LinkRewrites) > 0 {
		scraper.RewriteArticleLinks(aggregated.ArticleData, spider.LinkRewrites)
	}

	// Sort by time
	scraper.SortArticlesByTime(aggregated)

	return aggregated, allErrors
}

// writeJSON marshals data to JSON and writes to a file.
func writeJSON(path string, data any) {
	f, err := os.Create(path)
	if err != nil {
		log.Printf("创建文件失败 %s: %v", path, err)
		return
	}
	defer f.Close()

	enc := json.NewEncoder(f)
	enc.SetIndent("", "  ")
	enc.SetEscapeHTML(false)
	if err := enc.Encode(data); err != nil {
		log.Printf("写入 JSON 失败 %s: %v", path, err)
	}
}
