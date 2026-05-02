package scraper

import (
	"log"
	"net/url"
	"regexp"
	"strings"
)

// matchArticle checks if an article matches a rewrite rule's match condition.
func matchArticle(article *Article, match MatchRule) bool {
	if match.Name == "" && match.Host == "" {
		return false
	}

	author := strings.TrimSpace(article.Author)
	link := strings.TrimSpace(article.Link)

	nameOK := match.Name != "" && author == match.Name

	var hostOK bool
	if match.Host != "" {
		if u, err := url.Parse(link); err == nil {
			hostOK = u.Hostname() == match.Host
		}
	}

	return nameOK || hostOK
}

// RewriteArticleLinks applies link rewriting rules to articles.
func RewriteArticleLinks(articles []Article, rewrites []LinkRewrite) {
	if len(rewrites) == 0 {
		return
	}

	for i := range articles {
		link := strings.TrimSpace(articles[i].Link)
		if link == "" {
			continue
		}

		for _, group := range rewrites {
			if !matchArticle(&articles[i], group.Match) {
				continue
			}

			updatedLink := link
			for _, rule := range group.Rules {
				switch strings.ToLower(rule.Type) {
				case "prefix":
					if rule.From != "" && rule.To != "" && strings.HasPrefix(updatedLink, rule.From) {
						newLink := rule.To + updatedLink[len(rule.From):]
						if newLink != updatedLink {
							log.Printf("Rewrite link by prefix: %s -> %s", updatedLink, newLink)
							updatedLink = newLink
						}
					}
				case "regex":
					if rule.Pattern != "" && rule.Replace != "" {
						re, err := regexp.Compile(rule.Pattern)
						if err != nil {
							log.Printf("无效的正则表达式：%s: %v", rule.Pattern, err)
							continue
						}
						count := rule.Count
						if count <= 0 {
							count = 1
						}
						// Go's regexp doesn't have a direct "replace N times" so we do it manually
						newLink := updatedLink
						for c := 0; c < count; c++ {
							loc := re.FindStringIndex(newLink)
							if loc == nil {
								break
							}
							replaced := re.ReplaceAllString(newLink[loc[0]:loc[1]], rule.Replace)
							newLink = newLink[:loc[0]] + replaced + newLink[loc[1]:]
						}
						if newLink != updatedLink {
							log.Printf("Rewrite link by regex: %s -> %s", updatedLink, newLink)
							updatedLink = newLink
						}
					}
				}
			}

			if updatedLink != link {
				articles[i].Link = updatedLink
			}
		}
	}
}
