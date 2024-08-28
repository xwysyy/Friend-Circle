---

<img align='right' src="./static/avatar.png" width="150" alt="fclite">

# Friend-Circle-Lite 

[前端展示](https://fc.liushen.fun) | [详细文档](https://blog.qyliu.top/posts/4dc716ec/)

友链朋友圈简单版，实现了[友链朋友圈](https://github.com/Rock-Candy-Tea/hexo-circle-of-friends)的基本功能，能够定时爬取rss文章并输出有序内容，为了较好的兼容性，输入格式与友链朋友圈的json格式一致，为了轻量化，暂不支持从友链页面自动爬取，

## 展示页面

* [清羽飞扬の友链朋友圈](https://blog.qyliu.top/fcircle-lite/)

* [❖星港◎Star☆ 的友链朋友圈](https://blog.starsharbor.com/fcircle/)
* 欢迎更多

## 项目介绍

- **爬取文章**: 爬取所有友链的文章，结果放置在根目录的all.json文件中，方便读取并部署到前端。

## 特点介绍

* **轻量化**：对比原版友链朋友圈的功能，该友圈功能简洁，去掉了设置和fastAPI的臃肿，仅保留关键内容。
* **无数据库**：因为内容较少，我采用`json`直接存储文章信息，减少数据库操作，提升`action`运行效率。
* **部署简单**：原版友链朋友圈由于功能多，导致部署较为麻烦，本方案仅需简单的部署action即可使用，vercel仅用于部署前端静态页面和实时获取最新内容。
* **文件占用**：对比原版`4MB`的`bundle.js`文件大小，本项目仅需要`5.50KB`的`fclite.min.js`文件即可轻量的展示到前端。

## 功能概览

* 文章爬取
* 显示作者所有文章
* 获取丢失友链数据
* 随机钓鱼

## 使用方法

### 前置工作

1. **Fork 本仓库:**
   点击页面右上角的 Fork 按钮，将本仓库复制到你自己的`GitHub`账号下。

2. **配置 Secrets:**
   在你 Fork 的仓库中，依次进入 `Settings` -> `Secrets` -> `New repository secret`，添加以下 Secrets：
   - `PAT_TOKEN`: GitHub 的个人访问令牌，用于访问 GitHub API。
   - `SMTP_PWD`: SMTP 服务器的密码，用于发送电子邮件。

   ![](./static/1.png)
   
2. **配置action权限：**
   
   在设置中，点击`action`，拉到最下面，勾选`Read and write permissions`选项并保存，确保action有读写权限。
   
3. **启用 GitHub Actions:**
   GitHub Actions 已经配置好在仓库的 `.github/workflows/*.yml` 文件中，当到一定时间时将自动执行，也可以手动运行。
   其中，action功能如下：
   - `friend_circle_lite.yml`实现核心功能，爬取并发送邮箱；
   

### 配置选项

如果需要修改爬虫设置或邮件模板等配置，需要修改仓库中的 `config.yaml` 文件：

   - **爬虫相关配置**
     使用 `requests` 库实现友链文章的爬取，并将结果存储到根目录下的 `all.json` 文件中。
     
     ```yaml
     spider_settings:
       enable: true
       json_url: "https://blog.qyliu.top/friend.json"
       article_count: 5
     ```
     
     `enable`：开启或关闭，默认开启；
     
     `json_url`：友链朋友圈通用爬取格式第一种（下方有配置方法）;
     
     `article_count`：每个作者留存文章个数。
     
## 部署到网页

首先，将该项目部署到vercel，部署到vercel的目的主要是利用vercel检测仓库并实时刷新的功能，及时获取all.json文件内容。任意平台均可。

部署完成后，你将获得一个地址，建议自行绑定域名。

在前端页面的md文件中写入：

```html
<div id="friend-circle-lite-root"></div>
<script>
    if (typeof UserConfig === 'undefined') {
        var UserConfig = {
            // 填写你的fc Lite地址
            private_api_url: 'https://fc.liushen.fun/',
            // 点击加载更多时，一次最多加载几篇文章，默认20
            page_turning_number: 20,
            // 头像加载失败时，默认头像地址
            error_img: 'https://pic.imgdb.cn/item/6695daa4d9c307b7e953ee3d.jpg', // https://cdn.qyliu.top/i/2024/03/22/65fcea97b3ca6.png
        }
    }
</script>
<link rel="stylesheet" href="https://fastly.jsdelivr.net/gh/willow-god/Friend-Circle-Lite/main/fclite.min.css">
<script src="https://fastly.jsdelivr.net/gh/willow-god/Friend-Circle-Lite/main/fclite.min.js"></script>
```

其中第一个地址填入你自己的地址即可，**注意**尾部带`/`，不要遗漏。


