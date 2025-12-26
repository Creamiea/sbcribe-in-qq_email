import requests
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from deep_translator import GoogleTranslator
import datetime
import os
import time

# ================= 配置区域 =================
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
AUTH_CODE = os.environ.get('AUTH_CODE')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL')
# ===========================================

def get_weekly_trending_repos():
    """获取过去7天内创建的最热门Python项目"""
    print("正在获取 GitHub 数据...")
    last_week = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    
    # 搜索条件：Python语言，最近7天创建，按Star排序
    url = "https://api.github.com/search/repositories"
    query = f"language:python+created:>{last_week}+sort:stars"
    full_url = f"{url}?q={query}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    try:
        r = requests.get(full_url, headers=headers, timeout=15)
        r.raise_for_status()
        # 只取前 8 个，避免邮件过长导致翻译超时
        return r.json().get('items', [])[:8]
    except Exception as e:
        print(f"获取数据失败: {e}")
        return []

def translate_text(text):
    """调用 Google 翻译将文本转为中文"""
    if not text:
        return "暂无描述"
    
    try:
        # 限制长度防止报错
        text = text[:450] 
        # 使用 deep_translator 进行翻译
        translated = GoogleTranslator(source='auto', target='zh-CN').translate(text)
        return translated
    except Exception as e:
        print(f"翻译失败: {e}")
        return text  # 翻译失败则返回原文

def format_email_content(repos):
    """生成精美的 HTML 邮件报告"""
    if not repos:
        return "本周没有发现符合条件的热门项目。"

    # 邮件 CSS 样式
    html_content = """
    <html>
    <head>
    <style>
        body { font-family: '微软雅黑', sans-serif; color: #333; line-height: 1.6; }
        .card { border: 1px solid #e1e4e8; border-radius: 6px; padding: 16px; margin-bottom: 20px; background-color: #fff; }
        .title { font-size: 18px; font-weight: bold; color: #0366d6; text-decoration: none; }
        .stats { font-size: 12px; color: #586069; margin-top: 5px; }
        .tag { display: inline-block; background-color: #f1f8ff; color: #0366d6; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-right: 5px; margin-bottom: 5px;}
        .desc-cn { font-size: 14px; margin-top: 10px; color: #24292e; font-weight: 500;}
        .desc-en { font-size: 12px; color: #6a737d; margin-top: 5px; }
        .header { text-align: center; padding: 20px 0; border-bottom: 2px solid #0366d6; margin-bottom: 20px; }
    </style>
    </head>
    <body style="background-color: #f6f8fa; padding: 20px;">
        <div class="header">
            <h2>🚀 GitHub 本周 Python 热门新项目</h2>
            <p>只为你精选过去7天内诞生的黑马项目</p>
        </div>
    """
    
    for repo in repos:
        name = repo['name']
        stars = repo['stargazers_count']
        url = repo['html_url']
        desc_en = repo['description'] if repo['description'] else "No description provided."
        topics = repo.get('topics', [])[:5] # 获取前5个标签
        
        print(f"正在处理项目: {name}...")
        
        # 1. 翻译描述
        desc_cn = translate_text(desc_en)
        
        # 2. 生成标签 HTML
        tags_html = ""
        if topics:
            for tag in topics:
                tags_html += f'<span class="tag">{tag}</span>'
        else:
            tags_html = '<span class="tag" style="background-color:#eee;color:#666">暂无标签</span>'

        # 3. 组装单个项目卡片
        card = f"""
        <div class="card">
            <div>
                <a href="{url}" class="title">{name}</a>
                <span style="float:right; color:#cb2431; font-weight:bold;">🔥 {stars} Stars</span>
            </div>
            <div class="stats">
                创建时间: {repo['created_at'][:10]} | 作者: {repo['owner']['login']}
            </div>
            <div style="margin: 10px 0;">
                {tags_html}
            </div>
            <div class="desc-cn">💡 介绍：{desc_cn}</div>
            <div class="desc-en">{desc_en}</div>
        </div>
        """
        html_content += card
        
        # 稍微停顿一下，避免翻译接口请求过快
        time.sleep(1)

    html_content += """
        <div style="text-align: center; font-size: 12px; color: #999; margin-top: 30px;">
            <p>此邮件由 GitHub Actions 自动生成并发送</p>
        </div>
    </body>
    </html>
    """
    return html_content

def send_email():
    if not SENDER_EMAIL or not AUTH_CODE:
        print("错误：未检测到环境变量，请在 GitHub Secrets 中配置！")
        return

    repos = get_weekly_trending_repos()
    if not repos:
        print("未获取到项目，跳过。")
        return

    mail_content = format_email_content(repos)
    
    message = MIMEText(mail_content, 'html', 'utf-8')
    message['From'] = formataddr(["GitHub情报员", SENDER_EMAIL])
    message['To'] = formataddr(["开发者", RECEIVER_EMAIL])
    
    subject = f"GitHub 本周 Python 热点周报 ({datetime.datetime.now().strftime('%m-%d')})"
    message['Subject'] = Header(subject, 'utf-8')

    try:
        smtp_obj = smtplib.SMTP_SSL('smtp.qq.com', 465)
        smtp_obj.login(SENDER_EMAIL, AUTH_CODE)
        smtp_obj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message.as_string())
        smtp_obj.quit()
        print(f"[{datetime.datetime.now()}] 邮件发送成功！")
    except Exception as e:
        print(f"发送失败: {e}")

if __name__ == "__main__":
    send_email()