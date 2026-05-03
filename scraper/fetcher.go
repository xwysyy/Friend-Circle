package scraper

import (
	"context"
	"crypto/tls"
	"fmt"
	"io"
	"log"
	"math"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"
)

const (
	maxRetries    = 3
	backoffFactor = 0.6
	requestTimeout   = 50 * time.Second
	MaxFeedBodyBytes = 8 * 1024 * 1024
)

var retryStatusCodes = map[int]bool{
	403: true, 408: true, 425: true, 429: true,
	500: true, 502: true, 503: true, 504: true,
}

var defaultHeaders = map[string]string{
	"User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
	"Accept":          "application/atom+xml,application/rss+xml,application/xml;q=0.9,text/xml;q=0.8,*/*;q=0.7",
	"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
	"Cache-Control":   "no-cache",
	"Pragma":          "no-cache",
}

func setDefaultHeaders(req *http.Request) {
	for k, v := range defaultHeaders {
		req.Header.Set(k, v)
	}
}

func setAltHeaders(req *http.Request) {
	for k, v := range defaultHeaders {
		req.Header.Set(k, v)
	}
	req.Header.Set("Accept", "*/*")
}

// NewHTTPClient creates an http.Client optimized for feed scraping.
func NewHTTPClient() *http.Client {
	transport := &http.Transport{
		TLSClientConfig: &tls.Config{
			MinVersion: tls.VersionTLS12,
		},
		DialContext: (&net.Dialer{
			Timeout:   20 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		MaxIdleConns:        100,
		MaxIdleConnsPerHost: 10,
		MaxConnsPerHost:     10,
		IdleConnTimeout:     90 * time.Second,
		TLSHandshakeTimeout: 10 * time.Second,
		ResponseHeaderTimeout: 30 * time.Second,
		ForceAttemptHTTP2:   true,
		DisableCompression:  false,
	}

	return &http.Client{
		Transport: transport,
		Timeout:   requestTimeout,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			if len(via) >= 10 {
				return fmt.Errorf("过多重定向（>10）")
			}
			return nil
		},
	}
}

// FetchResponse contains the result of an HTTP fetch.
type FetchResponse struct {
	Body       []byte
	StatusCode int
}

// FetchWithRetry fetches a URL with exponential backoff retry logic.
func FetchWithRetry(ctx context.Context, client *http.Client, url string, useAltHeaders bool) (*FetchResponse, error) {
	var lastErr error

	for attempt := 0; attempt <= maxRetries; attempt++ {
		if attempt > 0 {
			backoff := time.Duration(float64(time.Second) * backoffFactor * math.Pow(2, float64(attempt-1)))
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			case <-time.After(backoff):
			}
		}

		req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
		if err != nil {
			return nil, fmt.Errorf("创建请求失败: %w", err)
		}

		if useAltHeaders {
			setAltHeaders(req)
		} else {
			setDefaultHeaders(req)
		}

		resp, err := client.Do(req)
		if err != nil {
			lastErr = fmt.Errorf("请求失败: %w", err)
			continue
		}

		body, readErr := io.ReadAll(io.LimitReader(resp.Body, MaxFeedBodyBytes+1))
		resp.Body.Close()
		if readErr != nil {
			lastErr = fmt.Errorf("读取响应失败: %w", readErr)
			continue
		}
		if int64(len(body)) > MaxFeedBodyBytes {
			lastErr = fmt.Errorf("响应体超出 %d 字节上限", MaxFeedBodyBytes)
			continue
		}

		if resp.StatusCode >= 400 {
			if retryStatusCodes[resp.StatusCode] && attempt < maxRetries {
				lastErr = fmt.Errorf("HTTP %d %s", resp.StatusCode, resp.Status)
				log.Printf("请求 %s 返回 %d，将重试 (%d/%d)", url, resp.StatusCode, attempt+1, maxRetries)
				continue
			}
			return nil, fmt.Errorf("HTTP %d %s", resp.StatusCode, resp.Status)
		}

		return &FetchResponse{Body: body, StatusCode: resp.StatusCode}, nil
	}

	return nil, fmt.Errorf("重试 %d 次后仍然失败: %w", maxRetries, lastErr)
}

// FetchAndProcessAll concurrently fetches and processes all friends in a source.
func FetchAndProcessAll(
	client *http.Client,
	friends [][]string,
	articleCount int,
	maxWorkers int,
	ignoreIDs map[string]struct{},
) (*Result, [][]string) {
	totalFriends := len(friends)
	if maxWorkers <= 0 {
		maxWorkers = 10
	}
	if maxWorkers > totalFriends && totalFriends > 0 {
		maxWorkers = totalFriends
	}

	sem := make(chan struct{}, maxWorkers)
	var wg sync.WaitGroup
	var mu sync.Mutex

	var (
		activeFriends int
		errorFriends  int
		allArticles   []Article
		errorEntries  [][]string
	)

	for _, friend := range friends {
		wg.Add(1)
		go func(f []string) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			result := processFriend(client, f, articleCount, ignoreIDs)

			mu.Lock()
			defer mu.Unlock()
			if result.Status == "active" {
				activeFriends++
				allArticles = append(allArticles, result.Articles...)
			} else {
				errorFriends++
				errorEntries = append(errorEntries, result.Entry)
			}
		}(friend)
	}

	wg.Wait()

	log.Printf("数据处理完成")
	log.Printf("总共有 %d 位朋友，其中 %d 位博客可访问，%d 位博客无法访问",
		totalFriends, activeFriends, errorFriends)

	result := &Result{
		StatisticalData: StatisticalData{
			FriendsNum:      totalFriends,
			ActiveNum:       activeFriends,
			ErrorNum:        errorFriends,
			ArticleNum:      len(allArticles),
			LastUpdatedTime: time.Now().Format("2006-01-02 15:04:05"),
		},
		ArticleData: allArticles,
	}

	return result, errorEntries
}

// processFriend handles a single friend entry.
func processFriend(
	client *http.Client,
	friend []string,
	count int,
	ignoreIDs map[string]struct{},
) FriendResult {
	// Validate entry
	if len(friend) < 4 || strings.TrimSpace(friend[3]) == "" {
		name := "UNKNOWN"
		if len(friend) > 0 {
			name = friend[0]
		}
		log.Printf("%s 的条目缺少必填的 feed_url（第4项）", name)
		return FriendResult{
			Name:   name,
			Status: "error",
			Entry:  friend,
		}
	}

	name, _, avatar, feedURL := friend[0], friend[1], friend[2], strings.TrimSpace(friend[3])
	log.Printf("%s 使用自定义 feed：%s", name, feedURL)

	ctx, cancel := context.WithTimeout(context.Background(), requestTimeout)
	defer cancel()

	articles, err := ParseFeed(ctx, client, feedURL, name, avatar, count, ignoreIDs)
	if err != nil {
		log.Printf("%s 的 feed 抓取失败：%s: %v", name, feedURL, err)
		return FriendResult{
			Name:   name,
			Status: "error",
			Entry:  friend,
		}
	}

	for _, a := range articles {
		log.Printf("%s 发布文章：%s @ %s", name, a.Title, a.Created)
	}

	return FriendResult{
		Name:     name,
		Status:   "active",
		Articles: articles,
		Entry:    friend,
	}
}
