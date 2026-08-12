# VaultMind Teknik Altyapı Kılavuzu

## 1. Sistem Mimarisi

### 1.1 Genel Bakış
VaultMind şirketi, mikroservis mimarisine dayalı bir altyapı kullanmaktadır. Tüm servisler Kubernetes üzerinde çalışmakta ve Docker container'ları ile dağıtılmaktadır.

### 1.2 Sunucu Altyapısı
- **Üretim Ortamı (Production)**: AWS eu-central-1 bölgesinde
  - 3 adet Kubernetes master node (m5.xlarge)
  - 10 adet Kubernetes worker node (c5.2xlarge)
  - RDS PostgreSQL (db.r5.xlarge) — Ana veritabanı
  - ElastiCache Redis (cache.r5.large) — Önbellek
- **Test Ortamı (Staging)**: AWS eu-central-1
  - 1 adet Kubernetes master node
  - 3 adet Kubernetes worker node
- **Geliştirme Ortamı (Development)**: Yerel Docker Compose

### 1.3 Ağ Yapısı
- VPC CIDR: 10.0.0.0/16
- Public Subnet: 10.0.1.0/24 (Load Balancer, NAT Gateway)
- Private Subnet: 10.0.2.0/24 (Uygulama servisleri)
- Database Subnet: 10.0.3.0/24 (RDS, ElastiCache)
- VPN bağlantısı: WireGuard üzerinden (port 51820)

## 2. Veritabanı Yönetimi

### 2.1 PostgreSQL Konfigürasyonu
- Versiyon: PostgreSQL 16
- Bağlantı havuzu: PgBouncer (max_client_conn: 1000)
- Yedekleme: Günlük otomatik backup (S3'e), 30 gün saklama
- Replikasyon: 1 read replica (raporlama sorguları için)

### 2.2 Veritabanı Isimlendirme Kuralları
- Tablo adları: snake_case (örn: user_profiles)
- Sütun adları: snake_case (örn: created_at)
- Index adları: idx_{tablo}_{sütun} (örn: idx_users_email)
- Foreign key: fk_{kaynak_tablo}_{hedef_tablo}

### 2.3 Migrasyon Politikası
- Tüm şema değişiklikleri Alembic ile yönetilir
- Her migrasyon geri alınabilir (reversible) olmalıdır
- Üretim ortamına uygulama öncesi staging'de test edilmelidir
- Büyük tablo değişiklikleri (>1M satır) bakım penceresi gerektirir

## 3. CI/CD Pipeline

### 3.1 Git İş Akışı
- Ana branch: `main` (korumalı, doğrudan push yasak)
- Geliştirme: `develop` branch'ı
- Özellik geliştirme: `feature/JIRA-123-aciklama` formatında
- Hotfix: `hotfix/aciklama` formatında

### 3.2 Pipeline Aşamaları
1. **Lint & Format**: ESLint, Prettier, Black, isort
2. **Unit Tests**: Jest (frontend), pytest (backend)
3. **Build**: Docker image oluşturma
4. **Security Scan**: Trivy (container), Snyk (dependency)
5. **Staging Deploy**: Otomatik (develop branch merge sonrası)
6. **Production Deploy**: Manuel onay gerekli

### 3.3 Deployment Stratejisi
- Blue-Green deployment kullanılmaktadır
- Canary release: Yeni versiyon önce %10 trafiğe açılır
- Rollback: Önceki versiyona 2 dakikada geri dönülebilir
- Sıfır kesinti (zero-downtime) hedeflenmektedir

## 4. Güvenlik

### 4.1 Erişim Kontrolü
- Tüm servisler arası iletişim mTLS ile şifrelenmektedir
- API Gateway: Kong (rate limiting, authentication)
- Secret yönetimi: AWS Secrets Manager
- IAM rolleri: En az yetki prensibi (least privilege)

### 4.2 Loglama ve İzleme
- Merkezi log: ELK Stack (Elasticsearch, Logstash, Kibana)
- Metrikler: Prometheus + Grafana
- Alerting: PagerDuty entegrasyonu
- APM: Datadog (uygulama performans izleme)

### 4.3 Felaket Kurtarma (Disaster Recovery)
- RPO (Recovery Point Objective): 1 saat
- RTO (Recovery Time Objective): 4 saat
- Cross-region backup: eu-west-1 bölgesine replikasyon
- Yılda 2 kez DR tatbikatı yapılmaktadır
