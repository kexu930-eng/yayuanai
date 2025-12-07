import requests
import json
import sys
import urllib.parse

def wrap_dingtalk_url(original_url):
    """
    将URL包装成钉钉可识别的格式
    这样可以绕过可信域名限制
    """
    encoded_url = urllib.parse.quote(original_url, safe='')
    return f"dingtalk://dingtalkclient/page/link?url={encoded_url}&pc_slide=true"

def send_task_notification(task_name, subtask_name, planned_time, detail_url, accept_url, reject_url, employee_dingtalk_id, robot_token):
    """
    发送任务分配通知
    
    参数:
        task_name: 任务名称
        subtask_name: 任务描述
        planned_time: 预计完成时间
        detail_url: 查看任务详情的URL
        accept_url: 接受任务的URL
        reject_url: 拒绝任务的URL
        employee_dingtalk_id: 员工的钉钉用户ID
        robot_token: 机器人的access_token
    """
    url = "https://api.dingtalk.com/v1.0/robot/oToMessages/batchSend"
    headers = {
        "x-acs-dingtalk-access-token": robot_token,
        "Content-Type": "application/json"
    }
    
    # 构建text内容
    text_content = f"任务名称：{task_name}\n\n任务描述：{subtask_name}\n\n计划执行时间：{planned_time}"
    
    # 包装URL为钉钉格式（绕过可信域名限制）
    wrapped_detail_url = wrap_dingtalk_url(detail_url)
    wrapped_accept_url = wrap_dingtalk_url(accept_url)
    wrapped_reject_url = wrap_dingtalk_url(reject_url)
    
    payload = {
        "robotCode": "dingb3x9dvpkgz0iwpyu",
        "userIds": [employee_dingtalk_id],  # 使用传入的员工钉钉ID
        "msgKey": "sampleActionCard3",
        "msgParam": json.dumps({
            "title": "新任务分配",
            "text": text_content,
            "actionTitle1": "查看任务详情",
            "actionURL1": wrapped_detail_url,
            "actionTitle2": "√ 接受任务",
            "actionURL2": wrapped_accept_url,
            "actionTitle3": "× 拒绝任务",
            "actionURL3": wrapped_reject_url
        }, ensure_ascii=False)
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    print(f"钉钉通知发送结果 - 状态码: {resp.status_code}")
    print(f"响应内容: {resp.text}")
    print(f"发送给员工ID: {employee_dingtalk_id}")
    print(f"原始URL: {detail_url}")
    print(f"包装后URL: {wrapped_detail_url}")
    return resp

# 示例调用
if __name__ == "__main__":
    # 可以直接调用函数测试
    send_task_notification(
        task_name="系统升级任务",
        subtask_name="数据库迁移",
        planned_time="2025-11-27 10:00:00",
        detail_url="http://101.37.168.176:8082/employee?id=1",
        accept_url="http://101.37.168.176:8082/api/assignments/1/accept",
        reject_url="http://101.37.168.176:8082/api/assignments/1/reject",
        employee_dingtalk_id="0109353429171130295"  # 测试用的钉钉ID
    )
