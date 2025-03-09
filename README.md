以下README内容由Ai生成：
---


# Emby IPLimit 项目

## 项目简介
Emby IPLimit 是一个用于限制和监控 Emby 服务器用户 IP 地址的工具。它通过监控 Emby 的播放会话，确保用户的播放行为符合预设的安全策略。此项目提供实时监控、IP 地理位置查询、会话记录和异常告警等功能。

## 使用方法

### 1. 使用 Docker 运行

**拉取镜像**  
从 Docker Hub 拉取最新版本的镜像：
```bash
docker pull username/embylimit:latest
```

**启动容器**  
首次运行容器时，会自动生成默认的`config.yaml`配置文件并停止。您需要编辑该文件后重新启动容器。  

❗ **重要说明**：
- 第一次启动容器时，程序会在挂载的`/app/data`目录下生成一个默认的`config.yaml`配置文件，然后容器会自动停止
- 您需要进入挂载的宿主机目录，编辑`config.yaml`文件，填写必要的配置信息（如 Emby 服务器的 URL 和 API 密钥）
- 编辑完成后，重新启动容器即可开始使用：
```bash
docker run -d -t  -v /root/1/test:/app/data --name emby-iplimit pdzhou/emby-iplimit:latest
```

### 2. 本地运行
如果您选择在本地运行项目，可以通过以下步骤安装依赖并启动：

**安装依赖**
```bash
pip install -r requirements.txt
```

**运行主程序**
```bash
python main.py
```

## 示例配置文件
```yaml
database:
  name: emby_playback.db # 默认数据库，不改动
emby:
  server_url: # https://emby.example.com
  api_key: # your_api_key_here
  check_interval: 10
notifications:
  alert_threshold: 2 # 播放窗口数(需不同IP），达到这个值即禁用
  enable_alerts: true
security:
  auto_disable: true
  whitelist: # 白名单内的用户不会被禁用
  - admin
  - user1
  - user2
```

## 功能介绍
- ✅ **实时监控**：监控 Emby 用户的播放会话
- 🌍 **IP 地理位置查询**：通过外部 API 查询用户 IP 的地理位置
- 📝 **会话记录**：将播放会话记录到本地数据库
- 🚨 **异常告警**：检测并记录异常登录行为，支持自动禁用用户

## 开发环境
- Python：3.6+
- Docker：18.03+
- Docker Compose：可选

## 贡献指南
如果您希望为此项目贡献代码，欢迎提交 PR 或 Issue。请遵循以下规则：
1. 遵守代码风格和命名规范
2. 在提交 PR 前，确保代码通过测试
3. 为您的代码添加必要的文档说明

## 许可证
本项目遵循 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 注意事项
- 📂 **配置文件路径**：确保挂载的宿主机目录存在且有写入权限
- ✏️ **配置文件修改**：首次启动后，容器会生成默认的`config.yaml`文件并停止。您需要手动编辑该文件后重新启动容器
- 💾 **数据持久化**：通过挂载`/app/data`目录，您可以将配置文件和数据库持久化到宿主机
