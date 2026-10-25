# 前端静态页面 + 反向代理（把 /api/... 转给 backend 容器）
FROM nginx:1.27-alpine

# 用我们的配置覆盖默认站点
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 只拷静态资源
COPY index.html /usr/share/nginx/html/index.html
COPY css /usr/share/nginx/html/css
COPY js /usr/share/nginx/html/js

EXPOSE 80
