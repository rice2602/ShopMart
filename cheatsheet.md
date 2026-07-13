# ShopMart DevOps Interview Cheatsheet (Quick Prep)

Cheatsheet ngắn gọn, trực diện, trả lời đúng trọng tâm theo văn phong phỏng vấn thực tế của dân devops (ngắn, đủ ý, không lý thuyết suông).

---

## 1. Docker & Docker Compose

### Q&A Phỏng Vấn Cốt Lõi

#### Docker image là gì?
*   **Trả lời:** Là một template đóng gói sẵn code, thư viện và môi trường chạy. Nó ở dạng tĩnh (read-only) và dùng làm "bản thiết kế" để chạy container.

#### Dockerfile là gì và hoạt động thế nào?
*   **Trả lời:** Là file chứa các bước lệnh để build ra image. Mỗi dòng lệnh tạo ra một layer mới.

#### Docker cache là gì?
*   **Trả lời:** Là cơ chế lưu trữ lại kết quả của các layer đã build trước đó. Khi build lại image, Docker sẽ tái sử dụng các layer không thay đổi thay vì chạy lại lệnh đó, giúp tăng tốc độ build.

#### Khi nào Docker cache bị invalid?
*   **Trả lời:** Khi một dòng lệnh trong Dockerfile thay đổi, hoặc các file nguồn truyền vào lệnh `COPY`/`ADD` thay đổi. Lúc đó, layer tương ứng và toàn bộ các layer phía sau nó sẽ bị mất cache (invalidated) và phải chạy lại từ đầu.

#### Làm sao để build Docker image nhanh hơn?
*   **Trả lời:** 
    1. Sắp xếp thứ tự lệnh: Đưa các lệnh cài đặt dependencies ít thay đổi lên trên (ví dụ: `COPY package.json` rồi chạy cài thư viện), đưa các lệnh copy source code hay thay đổi xuống dưới cùng.
    2. Dùng `.dockerignore` để loại bỏ các file thừa (như `node_modules`, log, git) giúp lệnh `COPY . .` chạy nhanh và cache ổn định hơn.

#### Multi-stage build là gì?
*   **Trả lời:** Là kỹ thuật chia quá trình build Docker image thành nhiều giai đoạn (stages) trong cùng một Dockerfile bằng cách dùng nhiều câu lệnh `FROM`. Mỗi stage có thể dùng một base image khác nhau.

#### Vì sao production nên dùng multi-stage build?
*   **Trả lời:** Giúp tạo ra image chạy cuối cùng (final image) siêu nhẹ vì chỉ cần copy file chạy (binary hoặc build artifact) từ stage compile sang stage production tinh giản, loại bỏ hoàn toàn các SDK nặng và mã nguồn thừa. Vừa giảm dung lượng đĩa, vừa tăng tính bảo mật (giảm bề mặt tấn công).

#### Container là gì và khác gì so với Image?
*   **Trả lời:** 
    *   **Image:** Là bản thiết kế tĩnh (file read-only), không tiêu thụ CPU/RAM khi lưu trên ổ đĩa.
    *   **Container:** Là một thực thể chạy thực tế (runtime instance) được tạo từ Image. Nó được cấp phát CPU/RAM và có một lớp ghi (write layer) riêng biệt để chạy ứng dụng.

#### Docker Volume là gì và dùng để làm gì?
*   **Trả lời:** Là cơ chế gắn một thư mục ngoài máy host vào trong container để lưu dữ liệu bền vững (persist data). Vì dữ liệu ghi trực tiếp vào container sẽ mất sạch khi container bị xóa, Volume giúp dữ liệu (như data của database) tồn tại độc lập với vòng đời của container.

#### Biến môi trường (Environment Variable) là gì?
*   **Trả lời:** Là các cặp key-value được lưu trữ ngoài hệ thống, dùng để cấu hình động ứng dụng mà không cần thay đổi source code (ví dụ: DB_URL, API_KEY).

#### Cách truyền biến môi trường vào container?
*   **Trả lời:** Khai báo trực tiếp ở mục `environment` hoặc đọc từ file `.env` qua mục `env_file` trong file Compose; hoặc truyền tham số `-e` khi chạy lệnh `docker run`.

#### Docker Compose là gì và dùng để làm gì?
*   **Trả lời:** Là công cụ giúp định nghĩa và chạy hệ thống gồm nhiều container. Thay vì gõ tay từng lệnh `docker run` phức tạp cho từng dịch vụ, mình khai báo tất cả dịch vụ (database, backend, frontend) trong 1 file `docker-compose.yml` rồi chạy bằng `docker compose up`.

#### Các container giao tiếp với nhau thế nào trong Docker Compose?
*   **Trả lời:** Qua Docker Network. Các container trong cùng một file Compose sẽ tự động kết nối vào chung một mạng ảo (Bridge network) và có thể gọi nhau bằng **tên dịch vụ (service name)** được khai báo trong file Compose nhờ cơ chế phân giải tên miền (DNS) nội bộ của Docker.

#### Non-root user là gì và tại sao cần thiết lập trong Dockerfile?
*   **Trả lời:** Là việc cấu hình cho ứng dụng trong container chạy dưới quyền của một user thường thay vì user root mặc định. Điều này ngăn chặn hacker nếu xâm nhập được vào container cũng không thể leo thang đặc quyền để kiểm soát máy host.

#### Làm sao debug một container bị crash?
*   **Trả lời:** 
    1. Check logs nhanh bằng `docker logs <container-id>`.
    2. Dùng `docker ps -a` kiểm tra Exit Code (ví dụ code 137 thường do OOM - hết RAM).
    3. Nếu cần chui vào trong khám phá: Thay đổi entrypoint thành `sh` hoặc `bash` rồi chạy `docker run -it`.

---

### Bài tập docker-compose.yml (FastAPI + PostgreSQL + Redis)

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: app-db
    restart: always
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret_password
      POSTGRES_DB: app_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin -d app_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: app-redis
    restart: always
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  web:
    build:
      context: ./app
      dockerfile: Dockerfile
    container_name: app-fastapi
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://admin:secret_password@db:5432/app_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  pgdata:
  redisdata:
```

#### Giải thích siêu ngắn gọn:
*   `db` / `redis`: Chạy Postgres và Redis bản Alpine siêu nhẹ. Có mapping port ra máy host và setup volume (`pgdata`, `redisdata`) để lưu data không bị mất.
*   `healthcheck`: Check xem db/redis thực sự sẵn sàng chưa (`pg_isready` và `redis-cli ping`).
*   `web`: Tự build FastAPI từ Dockerfile trong thư mục `./app`.
*   `depends_on` kèm `condition`: Đảm bảo FastAPI chỉ start khi db và redis đã vượt qua vòng healthcheck (đã `healthy`).
*   `DATABASE_URL` / `REDIS_URL`: Gọi qua host là `db` và `redis` nhờ DNS nội bộ của Docker Compose.

---

## 2. Kubernetes cơ bản

### Q&A Phỏng Vấn Cốt Lõi

#### Pod là gì?
*   **Trả lời:** Đơn vị triển khai nhỏ nhất của K8s. Chứa một hoặc một nhóm container dùng chung IP, port (`localhost`) và chung ổ đĩa.

#### Replica là gì và ReplicaSet là gì?
*   **Trả lời:** 
    *   **Replica:** Số lượng bản sao Pod chạy song song để gánh tải và dự phòng.
    *   **ReplicaSet:** Controller chịu trách nhiệm duy trì đúng số lượng bản sao Pod chạy ổn định trên cluster tại mọi thời điểm.

#### Deployment là gì?
*   **Trả lời:** Thằng quản lý số lượng và vòng đời của Pod. Nó quản lý ReplicaSet bên dưới để thực hiện scale Pod lên/xuống, tự động tạo lại Pod mới nếu bị lỗi, và update phiên bản mới không gây downtime (rolling update).

#### Service là gì?
*   **Trả lời:** Là đầu mối nhận traffic. Pod sinh ra và chết đi sẽ đổi IP liên tục, Service cung cấp 1 IP tĩnh và tên DNS cố định để chuyển traffic vào đúng các Pod tương ứng (dùng selector label).

#### ClusterIP là gì?
*   **Trả lời:** Loại Service mặc định của K8s. Nó cấp một IP nội bộ chỉ có thể truy cập được từ bên trong cluster, dùng để các microservice gọi nội bộ nhau.

#### NodePort là gì?
*   **Trả lời:** Loại Service mở một cổng tĩnh (từ 30000-32767) trên tất cả các Worker Node. Traffic từ bên ngoài gọi vào bất kỳ IP của Node nào trên cổng này sẽ được định tuyến tới Pod tương ứng.

#### So sánh ClusterIP và NodePort?
*   **Trả lời:** 
    *   **ClusterIP:** Chỉ truy cập nội bộ trong cluster. Bảo mật hơn, dùng cho backend/database.
    *   **NodePort:** Mở cổng ra ngoài internet qua IP của Node. Dễ cấu hình nhưng khó quản lý quy mô lớn và kém bảo mật hơn, thường dùng làm cầu nối trước LoadBalancer.

#### HPA (Horizontal Pod Autoscaler) là gì?
*   **Trả lời:** Bộ tự động scale Pod theo chiều ngang. Nó sẽ tự động tăng hoặc giảm số lượng Pod chạy trong Deployment dựa trên lượng tài nguyên tiêu thụ thực tế.

#### HPA hoạt động như thế nào và dựa trên metric nào?
*   **Trả lời:** HPA liên tục thu thập metrics (thông qua Metrics Server) và so sánh với ngưỡng cấu hình. Metric phổ biến nhất là CPU và Memory (RAM). Dự án ShopMart đang dùng CPU với ngưỡng trung bình 70% để scale số Pod từ 2 lên tối đa 5 Pod.

#### ConfigMap là gì?
*   **Trả lời:** Đối tượng lưu trữ các cấu hình dạng key-value thông thường (như file config, biến môi trường) tách biệt khỏi mã nguồn của container.

#### Secret là gì?
*   **Trả lời:** Đối tượng dùng để lưu trữ các thông tin nhạy cảm (như mật khẩu, API key, chứng chỉ SSL) được mã hóa dưới dạng Base64 để tăng tính bảo mật.

#### So sánh ConfigMap và Secret?
*   **Trả lời:** 
    *   **ConfigMap:** Lưu thông tin cấu hình thường dạng plaintext. Dễ đọc, dễ sửa.
    *   **Secret:** Lưu thông tin bảo mật, mã hóa Base64 và có phân quyền truy cập chặt chẽ hơn để tránh lộ thông tin.

#### Probe trong K8s là gì?
*   **Trả lời:** Cơ chế kiểm tra sức khỏe của container do kubelet thực hiện định kỳ (bằng lệnh shell, HTTP request hoặc TCP socket check).

#### Liveness Probe và Readiness Probe khác nhau như thế nào?
*   **Trả lời:** 
    *   **Liveness Probe:** Check xem app có bị đơ/treo không. Nếu check thất bại, K8s sẽ restart Pod.
    *   **Readiness Probe:** Check xem app đã khởi động xong và sẵn sàng nhận traffic chưa. Nếu check thất bại, K8s sẽ tạm thời tách IP Pod ra khỏi Service để không nhận traffic nữa (không restart Pod).

#### DaemonSet là gì?
*   **Trả lời:** Controller đảm bảo chạy chính xác 1 bản sao Pod trên mỗi Worker Node. Khi thêm Node mới, nó tự chạy Pod trên Node đó. Phù hợp cho log agent (Fluentd) hoặc monitoring agent.

#### StatefulSet là gì?
*   **Trả lời:** Controller dùng để quản lý các ứng dụng cần giữ trạng thái (Stateful) như database. Nó đảm bảo định danh duy nhất, cố định cho từng Pod (db-0, db-1) và gắn cố định ổ đĩa (Persistent Volume) dù Pod có bị restart.

#### So sánh DaemonSet và StatefulSet?
*   **Trả lời:** 
    *   **DaemonSet:** Chạy đều khắp các node (1 node = 1 pod), không quan tâm đến thứ tự hay lưu trữ persistent chung. Dùng cho log/monitor.
    *   **StatefulSet:** Chạy theo thứ tự tăng dần (pod sau chỉ start khi pod trước healthy), gắn chặt với một ổ đĩa riêng. Dùng cho Database/Stateful app.

#### GitOps là gì?
*   **Trả lời:** Là phương pháp quản lý và triển khai hạ tầng/ứng dụng bằng cách lấy Git làm "nguồn chuẩn duy nhất" (Single Source of Truth). Mọi thay đổi hệ thống đều qua Git commit/PR.

#### ArgoCD là gì và nó hiện thực GitOps như thế nào?
*   **Trả lời:** Là công cụ CD (Continuous Delivery) chạy trong K8s. Nó liên tục so sánh trạng thái khai báo trên Git với trạng thái chạy thực tế trên cluster. Khi phát hiện commit mới trên Git, nó sẽ tự động đồng bộ (apply) xuống cluster. Nếu có ai sửa tay trên cluster, nó tự động ghi đè lại cho đúng như Git (Self-healing).

---

### Demo Lệnh kubectl & Helm
*   `kubectl get pods`: Xem các Pod có chạy ngon không, status thế nào.
*   `kubectl describe pod <name>`: Xem chi tiết cấu hình Pod và đặc biệt là mục **Events** ở cuối để xem vì sao Pod bị lỗi (lỗi pull image, lỗi thiếu tài nguyên...).
*   `kubectl logs <name>`: Xem log của container để debug lỗi code bên trong.
*   `kubectl apply -f shopmart-observability.yaml`: Apply file config YAML lên cluster.
*   `helm install my-app ./chart-path`: Deploy nhanh một Helm chart.

---

## 3. AWS (SAA-level cơ bản)

### Q&A Phỏng Vấn Cốt Lõi

#### Amazon S3 là gì?
*   **Trả lời:** Dịch vụ lưu trữ đối tượng (object storage) đám mây, lưu trữ file giá rẻ với độ bền và độ sẵn sàng cực cao (99.999999999%).

#### AWS Lambda là gì?
*   **Trả lời:** Dịch vụ chạy code serverless (FaaS). Chỉ cần tải code lên, AWS tự lo hạ tầng, tự scale và chỉ tính tiền trên số mili-giây code thực thi thực tế (không chạy không tốn tiền).

#### Amazon DynamoDB là gì?
*   **Trả lời:** Dịch vụ cơ sở dữ liệu NoSQL dạng Key-Value được quản lý hoàn toàn (fully managed), cung cấp độ trễ siêu thấp (<10ms) ở mọi quy mô.

#### Amazon SNS là gì?
*   **Trả lời:** Dịch vụ thông báo Pub/Sub (Publish/Subscribe). Cho phép gửi tin nhắn, email hoặc kích hoạt các service khác khi có sự kiện xảy ra (ví dụ gửi mail cảnh báo cho đội vận hành).

#### Amazon CloudWatch là gì?
*   **Trả lời:** Dịch vụ giám sát và quản lý log/metrics cho tài nguyên AWS. Dùng để gom log, theo dõi hiệu năng và thiết lập cảnh báo (Alarm) khi hệ thống gặp lỗi.

#### Amazon EC2 (Elastic Compute Cloud) là gì?
*   **Trả lời:** Dịch vụ cung cấp các máy chủ ảo (Virtual Server) trên đám mây. Người dùng có toàn quyền cấu hình hệ điều hành, cài phần mềm và phải tự quản lý, bảo trì máy chủ này.

#### Định dạng file CSV và Parquet là gì?
*   **Trả lời:** 
    *   **CSV (Comma-Separated Values):** Định dạng lưu dữ liệu dạng bảng dưới dạng text thuần túy, phân tách bằng dấu phẩy. Dễ đọc nhưng dung lượng lớn, đọc ghi chậm.
    *   **Parquet:** Định dạng lưu dữ liệu dạng cột (columnar) nhị phân, nén tốt. Phù hợp cho phân tích dữ liệu lớn vì tốc độ truy vấn cực nhanh và tiết kiệm dung lượng.

#### AWS Glue Data Catalog là gì?
*   **Trả lời:** Kho lưu trữ siêu dữ liệu (metadata) tập trung để quản lý schema (cấu trúc bảng) của các file dữ liệu lưu trên S3, giúp các công cụ truy vấn hiểu được cấu trúc của file.

#### Amazon Athena là gì?
*   **Trả lời:** Dịch vụ truy vấn SQL serverless. Cho phép dùng câu lệnh SQL tiêu chuẩn để truy vấn trực tiếp dữ liệu dạng file (CSV, Parquet, JSON) trên S3 mà không cần import vào cơ sở dữ liệu.

#### Amazon VPC (Virtual Private Cloud) là gì?
*   **Trả lời:** Mạng ảo riêng độc lập được cấp phát cho tài khoản AWS của bạn, cho phép bạn thiết lập dải IP, subnet, bảng định tuyến và firewall để bảo mật tài nguyên.

#### VPC Endpoints là gì và tại sao nên dùng cho S3/DynamoDB?
*   **Trả lời:** Là cổng kết nối riêng tư giữa VPC và các dịch vụ AWS khác. Thay vì đi qua đường internet công cộng (tốn tiền NAT Gateway và kém bảo mật), VPC Gateway Endpoint mở đường đi nội bộ trực tiếp từ Lambda/EC2 đến S3/DynamoDB vừa bảo mật tối đa vừa miễn phí tiền truyền tải dữ liệu.

#### Athena Partitioning là gì và giúp ích gì?
*   **Trả lời:** Kỹ thuật chia dữ liệu trên S3 thành các thư mục con theo cấu trúc phân cấp (ví dụ: `year=2026/month=07/`). Khi Athena truy vấn lọc theo ngày, nó chỉ quét các file trong đúng thư mục đó thay vì quét toàn bộ bucket S3, giúp tăng tốc độ chạy câu lệnh và tiết kiệm tối đa chi phí quét đĩa (Athena tính tiền trên dung lượng dữ liệu quét).

---

### Mô tả kiến trúc ShopMart (Luồng dữ liệu)

> **Mô tả nhanh:** "Cửa hàng upload file CSV lên **S3 Raw**. S3 trigger **Lambda** chạy. Lambda đầu tiên check tên file trong **DynamoDB** xem có bị trùng không (idempotency để tránh tính đúp doanh thu). Nếu file mới, Lambda xử lý làm sạch: file chuẩn thì đổi sang định dạng **Parquet** đẩy vào **S3 Processed**, file lỗi đẩy vào **S3 Quarantine** và gửi mail cảnh báo qua **SNS**. Cuối cùng, data sạch ở S3 Processed được map schema qua **Glue Catalog** để dùng **Athena** gõ SQL query phân tích. Toàn bộ log của Lambda được đẩy về **CloudWatch**."

---

## 4. Terraform

### Q&A Phỏng Vấn Cốt Lõi

#### Terraform là gì?
*   **Trả lời:** Là công cụ định nghĩa hạ tầng bằng code (Infrastructure as Code - IaC). Cho phép khai báo tài nguyên cloud muốn tạo bằng code (ngôn ngữ HCL) rồi chạy lệnh để Terraform tự động tạo đúng như thế.

#### State file là gì?
*   **Trả lời:** Là file JSON (`terraform.tfstate`) lưu trữ trạng thái thực tế của hạ tầng Cloud mà Terraform đang quản lý. Nó dùng để đối chiếu với code của bạn. Nếu mất file này, Terraform sẽ không biết tài nguyên nào đã được tạo và có thể sẽ tạo đè lên hoặc tạo mới hoàn toàn.

#### Các lệnh terraform init, plan, apply là gì và hoạt động thế nào?
*   **Trả lời:** 
    *   `init`: Khởi tạo thư mục làm việc, tải các plugin provider (như AWS, Azure) cần thiết để giao tiếp với Cloud API.
    *   `plan`: So sánh code với State file để hiển thị trước những thay đổi sẽ thực hiện (sẽ tạo mới, sửa hay xóa gì).
    *   `apply`: Thực thi các thay đổi thật lên Cloud và cập nhật lại State file.

#### Remote State & State Locking là gì và tại sao cần thiết khi làm việc nhóm?
*   **Trả lời:** 
    *   **Remote State:** Lưu file state tập trung (ví dụ trên S3 bucket) thay vì để ở máy cá nhân của từng dev.
    *   **State Locking:** Dùng một cơ chế khóa (ví dụ qua DynamoDB) để khi một người đang chạy lệnh `apply`, state file sẽ bị khóa lại. Ngăn người khác chạy đè đụng độ gây hỏng hoặc sai lệch file state.

#### Resource dependency là gì? (Implicit vs Explicit dependency là gì?)
*   **Trả lời:** Thứ tự ưu tiên tạo tài nguyên.
    *   **Implicit (Ngầm định):** Tự hiểu do code gọi giá trị của tài nguyên này trong cấu hình tài nguyên khác (ví dụ: tạo Subnet trước rồi lấy Subnet ID để tạo EC2).
    *   **Explicit (Tường minh):** Khai báo rõ ràng qua thuộc tính `depends_on` khi Terraform không tự phát hiện được mối liên hệ.

#### Input Variable là gì?
*   **Trả lời:** Biến đầu vào (giống như tham số hàm) dùng để cấu hình động cho mã nguồn Terraform mà không cần sửa cứng code (ví dụ: region, environment, subnet IP).

#### Output Value là gì?
*   **Trả lời:** Biến đầu ra dùng để xuất và hiển thị thông tin quan trọng ra màn hình sau khi Terraform thực thi xong (ví dụ: IP của EC2 vừa tạo, ARN của S3).

---

## 5. Linux & Bash

### Q&A Phỏng Vấn Cốt Lõi

#### Các lệnh Linux cốt lõi hay dùng là gì?
*   **Trả lời:** 
    *   `cat filename` / `tail -f app.log`: Xem nội dung file và xem log chạy realtime.
    *   `grep "ERROR" app.log`: Tìm kiếm dòng chứa chữ ERROR trong file log.
    *   `curl -I https://google.com`: Gửi request test nhanh xem HTTP status trả về là gì (200, 404, 500).
    *   `ss -tulpn`: Check xem cổng mạng nào đang mở, tiến trình nào đang chiếm port.
    *   `df -h` / `free -m`: Check dung lượng ổ đĩa trống và dung lượng RAM còn lại của server.
    *   `chmod 755 script.sh`: Phân quyền cho file script.

#### Ý nghĩa của quyền file (chmod 755) là gì?
*   **Trả lời:** Quyền `755` cấp quyền cho file script/thư mục: Chủ sở hữu (Owner) có toàn quyền đọc, ghi, chạy (Read, Write, Execute = 7). Nhóm (Group) và những người khác (Others) chỉ có quyền đọc và chạy (Read, Execute = 5).

#### `set -e` trong Bash script là gì và tại sao nên dùng?
*   **Trả lời:** Là tuỳ chọn cấu hình ở đầu script. Nó ra lệnh cho script dừng chạy ngay lập tức nếu có bất kỳ dòng lệnh nào ở giữa gặp lỗi (exit code khác 0), tránh việc chạy cố dẫn đến lỗi dây chuyền khó debug.

#### Standard Output (stdout) và Standard Error (stderr) là gì?
*   **Trả lời:** Là hai luồng dữ liệu đầu ra mặc định của một tiến trình trong Linux.
    *   **Stdout (Descriptor 1):** Luồng chứa kết quả đầu ra thành công của câu lệnh.
    *   **Stderr (Descriptor 2):** Luồng chứa thông tin lỗi, cảnh báo phát sinh khi câu lệnh chạy thất bại.

#### Ký tự `2>&1` hoạt động thế nào và dùng để làm gì?
*   **Trả lời:** Là cú pháp điều hướng luồng dữ liệu (Redirect). Nó chuyển toàn bộ dữ liệu từ luồng lỗi (stderr - 2) vào chung luồng kết quả (stdout - 1). Thường dùng khi chạy tiến trình ngầm để ghi cả log chạy và log lỗi vào chung một file duy nhất (ví dụ: `python app.py > app.log 2>&1 &`).

---

## 6. Networking

### Q&A Phỏng Vấn Cốt Lõi

#### HTTP là gì?
*   **Trả lời:** Giao thức truyền tải siêu văn bản (Hypertext Transfer Protocol) dùng để giao tiếp client-server trên web, truyền dữ liệu dưới dạng text thuần túy (plaintext) nên không bảo mật.

#### HTTPS là gì và khác gì HTTP?
*   **Trả lời:** Là phiên bản bảo mật của HTTP (HTTP Secure). Nó mã hóa dữ liệu truyền tải bằng SSL/TLS để ngăn chặn việc nghe lén, giả mạo dữ liệu.

#### DNS (Domain Name System) là gì?
*   **Trả lời:** Hệ thống phân giải tên miền. Nó hoạt động giống như một danh bạ điện thoại, giúp dịch các tên miền dễ nhớ (như `shopmart.local`) thành các địa chỉ IP số để máy tính hiểu và kết nối.

#### DNS hoạt động thế nào để dịch tên miền thành IP?
*   **Trả lời:** Khi bạn gõ tên miền, trình duyệt sẽ check cache local trước. Nếu không có, nó gửi yêu cầu đến Resolver (nhà mạng). Resolver tiếp tục đi hỏi lần lượt các Name Server cấp cao từ trên xuống: Root Name Server (`.`) -> TLD Name Server (`.com`) -> Authoritative Name Server (nơi quản lý trực tiếp bản ghi của domain) để lấy về địa chỉ IP chính xác rồi trả về cho client.

#### TCP (Transmission Control Protocol) là gì?
*   **Trả lời:** Giao thức truyền tải hướng kết nối, đảm bảo dữ liệu gửi đi được truyền tải tin cậy, đúng thứ tự và không bị mất mát thông tin.

#### TCP Handshake (Bắt tay 3 bước) là gì và hoạt động thế nào?
*   **Trả lời:** Là quá trình thiết lập kết nối tin cậy trước khi truyền dữ liệu qua TCP:
    1. Client gửi cờ `SYN` (Yêu cầu kết nối).
    2. Server phản hồi bằng cờ `SYN-ACK` (Xác nhận và đồng ý kết nối).
    3. Client gửi cờ `ACK` (Xác nhận lại). Bắt tay hoàn tất, đường truyền sẵn sàng.

#### Port (Cổng kết nối) là gì?
*   **Trả lời:** Cổng logic trên hệ điều hành để phân định các dịch vụ hoặc ứng dụng khác nhau chạy trên cùng một server vật lý (ví dụ: Web chạy port 80/443, PostgreSQL port 5432, Redis port 6379).

#### Firewall (Tường lửa) là gì?
*   **Trả lời:** Hệ thống bảo mật giám sát và kiểm soát lưu lượng mạng ra/vào dựa trên các quy tắc bảo mật được thiết lập sẵn.

#### Quy tắc inbound và outbound của Firewall là gì?
*   **Trả lời:** 
    *   **Inbound rule:** Kiểm soát lưu lượng đi từ ngoài internet/mạng khác kết nối vào bên trong server (mặc định chặn hết, phải mở port cụ thể).
    *   **Outbound rule:** Kiểm soát lưu lượng đi từ trong server kết nối ra ngoài internet (mặc định mở hết để tải thư viện, gọi API bên ngoài).

#### IP Private vs IP Public là gì?
*   **Trả lời:** 
    *   **IP Private (IP nội bộ):** Dùng để các thiết bị giao tiếp với nhau trong mạng LAN/VPC nội bộ, internet không thể nhìn thấy hoặc gọi trực tiếp tới IP này.
    *   **IP Public (IP công cộng):** Địa chỉ IP duy nhất trên toàn thế giới để các thiết bị kết nối trực tiếp với internet.

#### NAT (Network Address Translation) là gì?
*   **Trả lời:** Kỹ thuật dịch chuyển địa chỉ IP. Thường dùng để cho phép các máy chủ trong mạng nội bộ (dùng IP Private) đi ra ngoài internet bằng một địa chỉ IP Public đại diện duy nhất.

#### Pull-based vs Push-based monitoring là gì?
*   **Trả lời:** 
    *   **Pull-based:** Server giám sát chủ động gửi request kéo (pull) metrics từ các ứng dụng/máy chủ về (ví dụ: Prometheus).
    *   **Push-based:** Các máy chủ/ứng dụng tự cài agent để chủ động gửi (push) metrics lên server giám sát tập trung (ví dụ: Datadog, CloudWatch).

#### Vì sao Push-based monitoring giải quyết được vấn đề Firewall/NAT của mạng nội bộ (Private Network)?
*   **Trả lời:** Vì các máy chủ nằm sau firewall/NAT trong Private Network chặn mọi kết nối inbound (đi vào), khiến server giám sát bên ngoài không thể "kéo" (pull) data được. Tuy nhiên, NAT/Firewall luôn cho phép kết nối outbound (đi ra) nên cơ chế "đẩy" (push) giúp agent từ bên trong chủ động kết nối ra ngoài để gửi metrics lên Cloud/Monitoring Server thành công.

#### Security Group là gì?
*   **Trả lời:** Là tường lửa ảo hoạt động ở cấp **máy chủ (Instance)** trong AWS để kiểm soát traffic inbound/outbound. Nó hoạt động kiểu **Stateful** (nếu mở cổng inbound thì tự động cho phép traffic trả về đi ra tương ứng mà không cần mở outbound).

#### Network ACL (NACL) là gì?
*   **Trả lời:** Tường lửa hoạt động ở cấp **mạng con (Subnet)** trong AWS. Nó hoạt động kiểu **Stateless** (phải khai báo tường minh cả luật inbound và outbound cho chiều đi/về).

#### So sánh Security Group và NACL trong AWS?
*   **Trả lời:** 
    *   **Security Group:** Bảo vệ ở cấp Instance. Stateful. Chỉ hỗ trợ luật cho phép (Allow).
    *   **NACL:** Bảo vệ ở cấp Subnet. Stateless (phải khai báo 2 chiều). Hỗ trợ cả luật cho phép (Allow) và luật chặn (Deny).

---

## 7. Redis & PostgreSQL

### Q&A Phỏng Vấn Cốt Lõi

#### Redis là gì?
*   **Trả lời:** Là hệ thống lưu trữ dữ liệu dạng Key-Value trong bộ nhớ RAM (In-Memory database) siêu nhanh, độ trễ cực thấp (<1ms).

#### Redis được dùng để Cache và Rate Limiting như thế nào?
*   **Trả lời:** 
    *   **Cache:** Lưu tạm các dữ liệu truy vấn nặng từ database chính. Khi client gọi, backend lấy từ Redis ra ngay lập tức thay vì chạy lại câu lệnh SQL nặng nề.
    *   **Rate Limiting:** Sử dụng các lệnh như `INCR` (tăng số đếm) kết hợp `EXPIRE` (thiết lập thời gian sống - TTL) cho một IP Client. Nếu số đếm vượt quá ngưỡng trong khoảng thời gian quy định thì chặn request tiếp theo.

#### PostgreSQL là gì và Persistent Data là gì?
*   **Trả lời:** 
    *   **PostgreSQL:** Hệ quản trị cơ sở dữ liệu quan hệ (RDBMS) mạnh mẽ, mã nguồn mở, hỗ trợ chuẩn SQL và lưu trữ dữ liệu bền vững.
    *   **Persistent Data:** Dữ liệu được lưu trữ cố định trên ổ đĩa cứng, đảm bảo không bị mất đi khi ứng dụng tắt, server khởi động lại hoặc mất điện đột ngột.

#### PostgreSQL đảm bảo lưu trữ dữ liệu an toàn (ACID) như thế nào?
*   **Trả lời:** Tuân thủ chặt chẽ tính chất ACID (Atomicity, Consistency, Isolation, Durability) và sử dụng cơ chế ghi nhật ký trước (WAL - Write-Ahead Logging) xuống ổ đĩa cứng trước khi cập nhật dữ liệu thật, giúp dữ liệu phục hồi nguyên vẹn khi xảy ra sự cố đột ngột.

#### So sánh và giải thích tại sao không lưu trữ toàn bộ dữ liệu vào Redis?
*   **Trả lời:** 
    1. **Chi phí:** RAM đắt hơn ổ cứng rất nhiều, không thể lưu hàng trăm GB dữ liệu lớn trên RAM một cách kinh tế.
    2. **An toàn:** Dữ liệu trên RAM dễ mất khi sập nguồn (dù Redis có cơ chế snapshot AOF/RDB nhưng vẫn không an toàn tuyệt đối như DB ghi đĩa).
    3. **Tính năng:** Redis không hỗ trợ các câu lệnh truy vấn phức tạp (SQL JOINs, ràng buộc khóa ngoại, transaction phức tạp).

---

## 8. ShopMart Deep-Dive (Kiến trúc dự án)

Câu hỏi cụ thể về code và hạ tầng của ShopMart:

#### "Explain the architecture."
*   **Trả lời:** "Store upload CSV lên **S3 Raw**. S3 trigger **Lambda** chạy. Lambda check trùng lặp trên **DynamoDB** (idempotency). Nếu file mới, Lambda lọc sạch: data tốt ghi vào **S3 Processed dưới dạng Parquet** (chia partition theo ngày), data lỗi ghi vào **S3 Quarantine dưới dạng CSV** và cảnh báo qua **SNS**. Data sạch được mapping qua **Glue Data Catalog** để Business dùng **Athena** gõ SQL query."

#### "Why DynamoDB?" (Không phải PostgreSQL? Không phải Redis?)
*   **Trả lời:** Vì hệ thống cần chạy phi máy chủ (Serverless). DynamoDB tự động scale, không sợ nghẽn số lượng connection (connection limit) khi hàng trăm Lambda gọi tới cùng lúc như Postgres, và chi phí chạy On-Demand của nó rẻ hơn nhiều so với việc duy trì server Postgres chạy 24/7. Nó cũng bền vững dữ liệu hơn Redis.

#### "What is idempotency?" (Được code như thế nào?)
*   **Trả lời:** Là cơ chế đảm bảo một file dù có upload nhiều lần thì hệ thống cũng chỉ xử lý đúng một lần để tránh tính trùng doanh số. Trong code ShopMart, [hàm `_check_idempotency`](file:///e:/Shopmart/src/pipeline.py#L50-L71) sẽ lấy tên file query vào bảng DynamoDB. Nếu thấy file đó đã có status là `SUCCESS` thì Lambda lập tức bỏ qua không xử lý nữa.

#### "Why Lambda?" (Tại sao không EC2?)
*   **Trả lời:** Vì các cửa hàng chỉ upload file bán hàng một lần vào khung giờ cố định buổi sáng. Dùng EC2 chạy 24/7 sẽ rất lãng phí tiền thuê server chạy không tải. Lambda chạy serverless, chỉ tính tiền khi có file upload lên (tiết kiệm chi phí tối đa).

#### "Why Parquet?" (Tại sao không CSV?)
*   **Trả lời:** Parquet lưu trữ dữ liệu dạng cột và nén tốt, giúp giảm đến 90% dung lượng lưu trữ trên S3. Đặc biệt, khi dùng Athena để truy vấn SQL, Athena chỉ quét đúng cột cần tính toán thay vì quét cả file CSV, giúp câu lệnh chạy nhanh hơn và giảm chi phí quét đĩa (Athena tính tiền trên dung lượng dữ liệu quét).

#### "What if Lambda fails?"
*   **Trả lời:** 
    *   Lambda chạy bất đồng bộ qua S3 trigger sẽ tự động retry 2 lần.
    *   Nếu vẫn lỗi, S3 Event được đẩy vào hàng đợi lỗi **SQS DLQ** để lưu vết sự kiện chờ xử lý tay.
    *   Hàm Lambda có cơ chế try-catch để ghi nhận status `FAILED` lên DynamoDB và gửi mail cảnh báo thông qua SNS.

#### "How would you scale this?"
*   **Trả lời:** Hệ thống hiện tại dùng hoàn toàn serverless (S3, Lambda, DynamoDB, Athena) nên khả năng scale là tự động. Tuy nhiên, cần lưu ý giới hạn số lượng Lambda chạy song song (concurrency limit, mặc định 1000) và write capacity của DynamoDB (cần cấu hình Auto-Scaling hoặc On-Demand mode).

#### "What resources are provisioned by Terraform?"
*   **Trả lời:** Terraform trong [main.tf](file:///e:/Shopmart/iac/main.tf) tạo ra:
    *   3 cái S3 buckets (raw, processed, quarantine).
    *   Bảng DynamoDB `shopmart-metadata`.
    *   SNS Topic `shopmart-pipeline-alerts` to báo lỗi.
    *   AWS Lambda function xử lý dữ liệu và gắn AWS SDK Pandas Layer.
    *   IAM Role và Policy phân quyền chi tiết cho Lambda.
    *   S3 Bucket Notification trigger để kết nối sự kiện upload sang Lambda.

#### "What does ArgoCD actually do?"
*   **Trả lời:** ArgoCD làm nhiệm vụ GitOps: Nó canh thư mục chứa các file YAML cấu hình K8s trên Git (`devops/k8s`). Khi phát hiện có commit mới trên Git, nó sẽ tự động đồng bộ (apply) xuống cluster. Nó cũng lo việc tự sửa lỗi (Self-healing) - nếu ai đó sửa tay cấu hình trên cluster, nó sẽ tự động đè lại cấu hình chuẩn từ Git.
