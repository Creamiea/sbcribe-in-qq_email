import requests
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import datetime
import os  # 新增：用于读取环境变量

# ================= 配置区域 =================
# 从环境变量中读取敏感信息（不要直接写死在这里）
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
AUTH_CODE = os.environ.get('AUTH_CODE')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL')
# ===========================================

def get_weekly_trending_repos():
    """获取过去7天内创建的最热门Python项目"""
    print("正在获取 GitHub 数据...")
    # 计算7天前的日期
    last_week = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    
    url = "https://api.github.com/search/repositories"
    query = f"language:python+created:>{last_week}+sort:stars"
    full_url = f"{url}?q={query}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    try:
        r = requests.get(full_url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json().get('items', [])[:10]
    except Exception as e:
        print(f"获取数据失败: {e}")
        return []

def format_email_content(repos):
    if not repos:
        return "本周没有发现符合条件的热门项目。"
    
    html_content = """
    <html><body>
        <h2>📅 本周 GitHub Python 热门新项目</h2>
        <table border="1" cellspacing="0" cellpadding="5" style="border-collapse:collapse; width:100%;">
            <tr style="background-color:#f2f2f2;"><th>项目名称</th><th>Star数</th><th>描述</th><th>链接</th></tr>
    """
    for repo in repos:
        desc = repo['description'] if repo['description'] else "无描述"
        html_content += f"""
        <tr>
            <td><strong>{repo['name']}</strong></td>
            <td style="color:red;">★ {repo['stargazers_count']}</td>
            <td>{desc}</td>
            <td><a href="{repo['html_url']}">点击查看</a></td>
        </tr>
        """
    html_content += "</table></body></html>"
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
    message['From'] = Header("GitHub 助手", 'utf-8')
    message['To'] = Header("开发者", 'utf-8')
    message['Subject'] = Header(f"GitHub 本周热门 ({datetime.datetime.now().strftime('%Y-%m-%d')})", 'utf-8')

    try:
        smtp_obj = smtplib.SMTP_SSL('smtp.qq.com', 465)
        smtp_obj.login(SENDER_EMAIL, AUTH_CODE)
        smtp_obj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message.as_string())
        smtp_obj.quit()
        print("邮件发送成功！")
    except Exception as e:
        print(f"发送失败: {e}")

if __name__ == "__main__":
    # 直接运行发送逻辑，不需要 schedule 循环
    send_email()