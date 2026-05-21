# SSL Sertifikaları

Bu dizin prod SSL sertifikalarını içerir. Git'e **commit EDİLMEZ** (`.gitignore`'a eklenmiştir).

## Let's Encrypt (Ücretsiz — Önerilen)

```bash
# 1. certbot kurulumu (Ubuntu/Debian)
sudo apt-get install certbot

# 2. Sertifika al (80 portu geçici açık olmalı)
sudo certbot certonly --standalone -d bgtest.dev -d www.bgtest.dev

# 3. Sertifikaları bu dizine kopyala
sudo cp /etc/letsencrypt/live/bgtest.dev/fullchain.pem ./cert.pem
sudo cp /etc/letsencrypt/live/bgtest.dev/privkey.pem  ./key.pem
sudo chmod 644 cert.pem key.pem

# 4. Otomatik yenileme (cron)
echo "0 3 * * * certbot renew --quiet && docker compose -f /path/to/docker-compose.prod.yml restart nginx" | sudo crontab -
```

## Self-Signed (Sadece test/staging)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem \
  -out cert.pem \
  -subj "/C=TR/ST=Istanbul/L=Istanbul/O=BGTS/CN=bgtest.dev"
```
