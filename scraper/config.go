package scraper

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

// LoadConfig reads and parses the YAML configuration file.
func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("读取配置文件失败: %w", err)
	}
	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("解析 YAML 配置失败: %w", err)
	}
	// defaults
	if cfg.SpiderSettings.ArticleCount <= 0 {
		cfg.SpiderSettings.ArticleCount = 5
	}
	if cfg.SpiderSettings.MaxWorkers <= 0 {
		cfg.SpiderSettings.MaxWorkers = 10
	}
	return &cfg, nil
}

// JSONSource represents a single JSON data source with its category name.
type JSONSource struct {
	Path     string
	Category string
}

// DiscoverJSONSources discovers all .json files in the directory of jsonURL,
// or returns a single source if jsonURL is a remote URL or a single file.
func DiscoverJSONSources(jsonURL string) []JSONSource {
	var sources []JSONSource

	if strings.HasPrefix(jsonURL, "http://") || strings.HasPrefix(jsonURL, "https://") {
		base := filepath.Base(jsonURL)
		category := strings.TrimSuffix(base, filepath.Ext(base))
		if category == "" {
			category = "default"
		}
		sources = append(sources, JSONSource{Path: jsonURL, Category: category})
		return sources
	}

	// Local path: try directory scan
	baseDir := filepath.Dir(jsonURL)
	if baseDir == "" {
		baseDir = "."
	}

	entries, err := os.ReadDir(baseDir)
	if err == nil {
		for _, e := range entries {
			if e.IsDir() || !strings.HasSuffix(strings.ToLower(e.Name()), ".json") {
				continue
			}
			category := strings.TrimSuffix(e.Name(), filepath.Ext(e.Name()))
			sources = append(sources, JSONSource{
				Path:     filepath.Join(baseDir, e.Name()),
				Category: category,
			})
		}
	}

	if len(sources) > 0 {
		log.Printf("已启用分类模式：共发现 %d 个 JSON 数据源于 %s", len(sources), baseDir)
		return sources
	}

	// Fallback to single source
	base := filepath.Base(jsonURL)
	category := strings.TrimSuffix(base, filepath.Ext(base))
	if category == "" {
		category = "default"
	}
	sources = append(sources, JSONSource{Path: jsonURL, Category: category})
	return sources
}

// LoadFriends reads and parses a friends JSON file (local or remote).
func LoadFriends(source string, client *http.Client) ([][]string, error) {
	var data []byte

	if strings.HasPrefix(source, "http://") || strings.HasPrefix(source, "https://") {
		req, err := http.NewRequest("GET", source, nil)
		if err != nil {
			return nil, fmt.Errorf("创建请求失败: %w", err)
		}
		setDefaultHeaders(req)
		resp, err := client.Do(req)
		if err != nil {
			return nil, fmt.Errorf("获取友链 JSON 失败: %w", err)
		}
		defer resp.Body.Close()
		if resp.StatusCode >= 400 {
			return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, resp.Status)
		}
		data, err = io.ReadAll(resp.Body)
		if err != nil {
			return nil, fmt.Errorf("读取响应体失败: %w", err)
		}
	} else {
		var err error
		data, err = os.ReadFile(source)
		if err != nil {
			return nil, fmt.Errorf("读取本地 JSON 文件失败: %w", err)
		}
	}

	var fd FriendsData
	if err := json.Unmarshal(data, &fd); err != nil {
		return nil, fmt.Errorf("解析 JSON 失败: %w", err)
	}
	return fd.Friends, nil
}

// FetchIgnoreIDs loads the ignore ID list from a URL or local file.
func FetchIgnoreIDs(source string, client *http.Client) map[string]struct{} {
	ids := make(map[string]struct{})
	source = strings.TrimSpace(source)
	if source == "" {
		return ids
	}

	var data []byte

	if strings.HasPrefix(source, "http://") || strings.HasPrefix(source, "https://") {
		req, err := http.NewRequest("GET", source, nil)
		if err != nil {
			log.Printf("获取忽略列表失败：%s；错误：%v", source, err)
			return ids
		}
		setDefaultHeaders(req)
		resp, err := client.Do(req)
		if err != nil {
			log.Printf("获取忽略列表失败：%s；错误：%v", source, err)
			return ids
		}
		defer resp.Body.Close()
		if resp.StatusCode >= 400 {
			log.Printf("获取忽略列表失败：%s；HTTP %d", source, resp.StatusCode)
			return ids
		}
		var readErr error
		data, readErr = io.ReadAll(resp.Body)
		if readErr != nil {
			log.Printf("读取忽略列表响应体失败：%s；错误：%v", source, readErr)
			return ids
		}
	} else {
		var err error
		data, err = os.ReadFile(source)
		if err != nil {
			log.Printf("获取忽略列表失败：%s；错误：%v", source, err)
			return ids
		}
	}

	// Try {"status": 200, "data": [...]} format first
	var wrapper struct {
		Data []string `json:"data"`
		IDs  []string `json:"ids"`
	}
	if err := json.Unmarshal(data, &wrapper); err == nil {
		list := wrapper.Data
		if len(list) == 0 {
			list = wrapper.IDs
		}
		for _, id := range list {
			id = strings.TrimSpace(id)
			if id != "" {
				ids[id] = struct{}{}
			}
		}
		if len(ids) > 0 {
			return ids
		}
	}

	// Try plain array format
	var arr []string
	if err := json.Unmarshal(data, &arr); err == nil {
		for _, id := range arr {
			id = strings.TrimSpace(id)
			if id != "" {
				ids[id] = struct{}{}
			}
		}
	}

	return ids
}
