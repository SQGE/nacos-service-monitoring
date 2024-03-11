from flask import Flask, Response
from prometheus_client import generate_latest, Gauge, CollectorRegistry
import requests
import yaml

app = Flask(__name__)

# 定义 Prometheus 指标
nacos_request_status = Gauge('nacos_service_status', 'Nacos服务发现请求状态（0: 异常, 1: 正常）', ['service_name', 'region'], registry=CollectorRegistry())

# 从文件加载配置
with open('config.yaml', 'r') as config_file:
    config = yaml.safe_load(config_file)

# 遍历地区并为每个地区设置 Nacos 配置
for region in config['regions']:
    region_name = region['name']
    nacos_config = region['nacos']
    services = region['services']

    @app.route('/metrics')
    def metrics():
        # 发起 Nacos 服务发现请求并检查该地区中每个服务的状态
        for service_name in services:
            nacos_url = nacos_config['url']
            namespace_id = nacos_config['namespace_id']

            params = {
                'serviceName': service_name,
                'namespaceId': namespace_id
            }

            try:
                nacos_response = requests.get(nacos_url, params=params)
                nacos_response.raise_for_status()

                # 检查 hosts 是否为空
                hosts = nacos_response.json().get('hosts', [])
                is_normal = len(hosts) > 0

                # 设置指标值并添加服务和地区标签
                nacos_request_status.labels(service_name=service_name, region=region_name).set(int(is_normal))

            except requests.RequestException as e:
                # 处理请求失败的情况，将指标值设置为异常
                nacos_request_status.labels(service_name=service_name, region=region_name).set(0)

        return Response(generate_latest(nacos_request_status), mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
