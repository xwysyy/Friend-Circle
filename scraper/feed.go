package scraper

import (
	"context"
	"crypto/sha1"
	"fmt"
	"log"
	"net/http"
	"sort"
	"strings"
	"time"

	"github.com/mmcdole/gofeed"
)

// MakeArticleID creates a stable SHA1-based ID for an article.
// Uses link as primary key; falls back to feed_url|title|published.
func MakeArticleID(link, title, published, feedURL string) string {
	base := strings.TrimSpace(link)
	if base == "" {
		base = strings.TrimSpace(fmt.Sprintf("%s|%s|%s", feedURL, title, published))
	}
	return fmt.Sprintf("%x", sha1.Sum([]byte(base)))
}

// shanghai is the Asia/Shanghai timezone used for time normalization.
var shanghai *time.Location

func init() {
	var err error
	shanghai, err = time.LoadLocation("Asia/Shanghai")
	if err != nil {
		// Fallback to UTC+8 fixed zone
		shanghai = time.FixedZone("CST", 8*3600)
	}
}

// FormatPublishedTime normalizes a time to Asia/Shanghai timezone with format "2006-01-02 15:04".
func FormatPublishedTime(t *time.Time) string {
	if t == nil {
		return ""
	}
	return t.In(shanghai).Format("2006-01-02 15:04")
}

// ParseFeed fetches and parses an RSS/Atom feed, returning articles.
func ParseFeed(
	ctx context.Context,
	client *http.Client,
	url string,
	authorName string,
	avatar string,
	count int,
	ignoreIDs map[string]struct{},
) ([]Article, error) {
	// First attempt with standard headers
	resp, err := FetchWithRetry(ctx, client, url, false)
	if err != nil {
		return nil, err
	}

	fp := gofeed.NewParser()
	feed, err := fp.ParseString(string(resp.Body))
	if err != nil || len(feed.Items) == 0 {
		// Retry with alternate headers (mimics Python's alt_headers retry)
		log.Printf("Feed 初次解析失败，准备重试：%s", url)
		time.Sleep(600 * time.Millisecond)

		resp2, err2 := FetchWithRetry(ctx, client, url, true)
		if err2 != nil {
			if err != nil {
				return nil, fmt.Errorf("解析失败: %w; 重试也失败: %v", err, err2)
			}
			return nil, err2
		}

		feed, err = fp.ParseString(string(resp2.Body))
		if err != nil {
			return nil, fmt.Errorf("Feed 解析失败: %w", err)
		}
		if len(feed.Items) == 0 {
			return nil, fmt.Errorf("Feed 解析后无文章条目")
		}
	}

	var articles []Article
	skipped := 0

	for _, item := range feed.Items {
		if len(articles) >= count {
			break
		}

		var published string
		if item.PublishedParsed != nil {
			published = FormatPublishedTime(item.PublishedParsed)
		} else if item.UpdatedParsed != nil {
			published = FormatPublishedTime(item.UpdatedParsed)
			log.Printf("文章 %s 未包含发布时间，使用更新时间 %s", item.Title, published)
		} else {
			published = ""
			log.Printf("文章 %s 未包含任何时间信息", item.Title)
		}

		title := item.Title
		link := item.Link
		articleID := MakeArticleID(link, title, published, url)

		if _, ignored := ignoreIDs[articleID]; ignored {
			skipped++
			continue
		}

		articles = append(articles, Article{
			ID:      articleID,
			Title:   title,
			Created: published,
			Link:    link,
			Author:  authorName,
			Avatar:  avatar,
		})
	}

	if skipped > 0 {
		log.Printf("Feed 已跳过 %d 篇被忽略文章：%s", skipped, url)
	}

	return articles, nil
}

// SortArticlesByTime sorts articles by created time descending.
// Articles with empty created time get a default value.
func SortArticlesByTime(result *Result) {
	for i := range result.ArticleData {
		if result.ArticleData[i].Created == "" {
			result.ArticleData[i].Created = "2024-01-01 00:00"
			log.Printf("文章 %s 无有效时间，设为默认 2024-01-01 00:00", result.ArticleData[i].Title)
		}
	}

	sort.SliceStable(result.ArticleData, func(i, j int) bool {
		ti, _ := time.Parse("2006-01-02 15:04", result.ArticleData[i].Created)
		tj, _ := time.Parse("2006-01-02 15:04", result.ArticleData[j].Created)
		return ti.After(tj)
	})
}
