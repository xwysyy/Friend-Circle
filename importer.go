package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/xwysyy/Friend-Circle/scraper"
)

const importTimeout = 60 * time.Second

type importPayload struct {
	Mode     string                  `json:"mode"`
	Stats    scraper.StatisticalData `json:"stats"`
	Articles []scraper.Article       `json:"articles"`
}

func importResult(client *http.Client, mode string, result *scraper.Result) error {
	importURL := strings.TrimSpace(os.Getenv("FRIEND_CIRCLE_IMPORT_URL"))
	importToken := strings.TrimSpace(os.Getenv("FRIEND_CIRCLE_IMPORT_TOKEN"))
	if importURL == "" && importToken == "" {
		log.Println("未配置 FRIEND_CIRCLE_IMPORT_URL / FRIEND_CIRCLE_IMPORT_TOKEN，跳过远端索引导入")
		return nil
	}
	if importURL == "" || importToken == "" {
		return fmt.Errorf("FRIEND_CIRCLE_IMPORT_URL 与 FRIEND_CIRCLE_IMPORT_TOKEN 必须同时配置")
	}
	if result == nil {
		return fmt.Errorf("导入 %s 失败：结果为空", mode)
	}

	body, err := json.Marshal(importPayload{
		Mode:     mode,
		Stats:    result.StatisticalData,
		Articles: result.ArticleData,
	})
	if err != nil {
		return fmt.Errorf("编码 %s 导入数据失败: %w", mode, err)
	}

	ctxClient := *client
	ctxClient.Timeout = importTimeout
	req, err := http.NewRequest(http.MethodPost, importURL, bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("创建 %s 导入请求失败: %w", mode, err)
	}
	req.Header.Set("Authorization", "Bearer "+importToken)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "Friend-Circle-Importer/1.0")

	resp, err := ctxClient.Do(req)
	if err != nil {
		return fmt.Errorf("提交 %s 导入请求失败: %w", mode, err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("导入 %s 返回 HTTP %d: %s", mode, resp.StatusCode, strings.TrimSpace(string(respBody)))
	}

	log.Printf("远端索引导入完成：%s，共 %d 篇", mode, len(result.ArticleData))
	return nil
}
