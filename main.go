package main

import (
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

	// --- First pass: full index ---
	result, errorEntries := collectFromConfig(cfg, client, nil)

	if result.StatisticalData.ActiveNum == 0 {
		log.Fatalf("active_num=0，中止")
	}

	log.Printf("抓取完成：all，共 %d 篇，错误 %d 条", len(result.ArticleData), len(errorEntries))
	if err := importResult(client, "all", result); err != nil {
		log.Fatalf("导入 all 到远端索引失败: %v", err)
	}

	// --- Second pass: personal (with ignore list) ---
	ignoreURL := os.Getenv("FRIEND_CIRCLE_IGNORE_URL")
	if ignoreURL == "" {
		ignoreURL = cfg.SpiderSettings.IgnoreURL
	}
	ignoreIDs := scraper.FetchIgnoreIDs(ignoreURL, client)
	personalResult := result
	personalErrors := errorEntries

	if len(ignoreIDs) > 0 {
		log.Printf("已加载忽略列表，共 %d 条，将生成 personal 远端索引", len(ignoreIDs))
		personalResult, personalErrors = collectFromConfig(cfg, client, ignoreIDs)
		if personalResult.StatisticalData.ActiveNum == 0 {
			log.Fatalf("personal active_num=0，中止")
		}
	} else {
		log.Println("忽略列表为空（或不可用），personal 远端索引将与 all 相同")
	}
	log.Printf("抓取完成：personal，共 %d 篇，错误 %d 条", len(personalResult.ArticleData), len(personalErrors))
	if err := importResult(client, "personal", personalResult); err != nil {
		log.Fatalf("导入 personal 到远端索引失败: %v", err)
	}
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
