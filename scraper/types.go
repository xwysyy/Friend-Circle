package scraper

// Article represents a single blog article in the output JSON.
type Article struct {
	ID       string `json:"id"`
	Title    string `json:"title"`
	Created  string `json:"created"`
	Link     string `json:"link"`
	Author   string `json:"author"`
	Avatar   string `json:"avatar"`
	Category string `json:"category"`
}

// StatisticalData holds aggregated statistics for the scraping run.
type StatisticalData struct {
	FriendsNum      int    `json:"friends_num"`
	ActiveNum       int    `json:"active_num"`
	ErrorNum        int    `json:"error_num"`
	ArticleNum      int    `json:"article_num"`
	LastUpdatedTime string `json:"last_updated_time"`
}

// Result is the top-level output structure written to all.json.
type Result struct {
	StatisticalData StatisticalData `json:"statistical_data"`
	ArticleData     []Article       `json:"article_data"`
}

// FriendEntry represents a single friend: [name, blog_url, avatar, feed_url].
type FriendEntry struct {
	Name    string
	BlogURL string
	Avatar  string
	FeedURL string
}

// FriendsData is the JSON structure of config/*.json files.
type FriendsData struct {
	Friends [][]string `json:"friends"`
}

// SpiderSettings mirrors the spider_settings section of conf.yaml.
type SpiderSettings struct {
	Enable       bool            `yaml:"enable"`
	JSONURL      string          `yaml:"json_url"`
	ArticleCount int             `yaml:"article_count"`
	MaxWorkers   int             `yaml:"max_workers"`
	IgnoreURL    string          `yaml:"ignore_url"`
	LinkRewrites []LinkRewrite   `yaml:"link_rewrites"`
}

// LinkRewrite defines a link rewriting rule group.
type LinkRewrite struct {
	Match MatchRule     `yaml:"match"`
	Rules []RewriteRule `yaml:"rules"`
}

// MatchRule specifies which articles a rewrite group applies to.
type MatchRule struct {
	Name string `yaml:"name"`
	Host string `yaml:"host"`
}

// RewriteRule defines a single prefix or regex rewrite operation.
type RewriteRule struct {
	Type    string `yaml:"type"`    // "prefix" or "regex"
	From    string `yaml:"from"`    // for prefix
	To      string `yaml:"to"`      // for prefix
	Pattern string `yaml:"pattern"` // for regex
	Replace string `yaml:"replace"` // for regex
	Count   int    `yaml:"count"`   // for regex, default 1
}

// Config is the top-level YAML configuration.
type Config struct {
	SpiderSettings SpiderSettings `yaml:"spider_settings"`
}

// FriendResult holds the processing result for a single friend.
type FriendResult struct {
	Name     string
	Status   string // "active" or "error"
	Articles []Article
	Entry    []string // original entry for error reporting
}
