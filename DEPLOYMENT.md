# Production Deployment Guide

This guide covers deploying the AI Governance Literacy Platform for production use, supporting 10,000+ concurrent users.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Requirements](#infrastructure-requirements)
3. [Database Setup](#database-setup)
4. [Environment Configuration](#environment-configuration)
5. [Docker Deployment](#docker-deployment)
6. [Scaling Considerations](#scaling-considerations)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Security Hardening](#security-hardening)
9. [Backup Procedures](#backup-procedures)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- PostgreSQL 14+ (for production database)
- Qdrant Cloud account or self-hosted Qdrant cluster
- Domain name with SSL certificate
- Reverse proxy (Nginx or Traefik) for production
- Monitoring solution (Prometheus, Grafana, or similar)

## Infrastructure Requirements

### Minimum Requirements (1,000 users)
- **Backend:** 2 CPU cores, 4GB RAM
- **Frontend:** 1 CPU core, 1GB RAM
- **Database:** 2 CPU cores, 4GB RAM, 50GB storage
- **Qdrant:** 2 CPU cores, 4GB RAM

### Recommended for 10,000+ Users
- **Backend:** 4-8 CPU cores, 8-16GB RAM (multiple instances)
- **Frontend:** 2 CPU cores, 2GB RAM (with CDN)
- **Database:** 4 CPU cores, 16GB RAM, 200GB+ SSD storage
- **Qdrant:** 4 CPU cores, 8GB RAM (or Qdrant Cloud)
- **Load Balancer:** Dedicated instance or managed service
- **Redis:** 2 CPU cores, 4GB RAM (for caching and sessions)

## Database Setup

### Migrating from SQLite to PostgreSQL

1. **Install PostgreSQL:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   
   # Or use Docker
   docker run -d \
     --name postgres \
     -e POSTGRES_PASSWORD=your_password \
     -e POSTGRES_DB=aigov \
     -p 5432:5432 \
     postgres:14-alpine
   ```

2. **Update DATABASE_URL:**
   ```env
   DATABASE_URL=postgresql://user:password@host:5432/aigov
   ```

3. **Run migrations:**
   ```bash
   docker-compose exec backend python scripts/init_db.py
   ```

4. **Migrate existing data (if applicable):**
   - Export from SQLite: `sqlite3 aigov.db .dump > backup.sql`
   - Import to PostgreSQL (requires manual conversion)

### Database Optimization

- Enable connection pooling (PgBouncer recommended)
- Configure appropriate `max_connections` (default: 100)
- Set up regular VACUUM and ANALYZE jobs
- Enable query logging for slow queries
- Configure backups (see Backup Procedures)

## Environment Configuration

### Production Environment Variables

Create a `.env` file with production values:

```env
# Environment
ENVIRONMENT=production

# Database (PostgreSQL for production)
DATABASE_URL=postgresql://user:password@postgres:5432/aigov

# Security - REQUIRED
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Keys - REQUIRED
GROQ_API_KEY=<your-groq-api-key>
QDRANT_URL=https://your-cluster-id.qdrant.io
QDRANT_API_KEY=<your-qdrant-api-key>

# CORS - Set to your production domain
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Generating Secure Keys

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate database password
openssl rand -base64 32
```

## Docker Deployment

### Production docker-compose.yml

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - QDRANT_URL=${QDRANT_URL}
      - QDRANT_API_KEY=${QDRANT_API_KEY}
      - ENVIRONMENT=production
      - CORS_ORIGINS=${CORS_ORIGINS}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    restart: always
    networks:
      - aigov-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 1G
    restart: always
    networks:
      - aigov-network

  postgres:
    image: postgres:14-alpine
    environment:
      - POSTGRES_DB=aigov
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    restart: always
    networks:
      - aigov-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - frontend
      - backend
    restart: always
    networks:
      - aigov-network

volumes:
  postgres_data:

networks:
  aigov-network:
    driver: bridge
```

### Deploy

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Scaling Considerations

### Horizontal Scaling

**Backend:**
- Run multiple backend instances behind a load balancer
- Use sticky sessions or stateless JWT tokens
- Implement Redis for shared session storage (if needed)

**Frontend:**
- Serve static files via CDN (Cloudflare, AWS CloudFront)
- Use multiple nginx instances
- Enable HTTP/2 and compression

**Database:**
- Use read replicas for query distribution
- Implement connection pooling (PgBouncer)
- Consider database sharding for very large datasets

### Vertical Scaling

- Monitor resource usage and scale up as needed
- Use container orchestration (Kubernetes) for automatic scaling
- Implement auto-scaling based on CPU/memory metrics

### Caching Strategy

1. **Redis for:**
   - Session storage
   - Frequently accessed queries
   - API response caching

2. **CDN for:**
   - Static frontend assets
   - API responses (where appropriate)

3. **Application-level caching:**
   - Cache embedding computations
   - Cache document metadata

## Monitoring and Logging

### Application Monitoring

**Metrics to Monitor:**
- Request rate and latency
- Error rates (4xx, 5xx)
- Database query performance
- Qdrant query performance
- Memory and CPU usage
- Active connections

**Tools:**
- Prometheus + Grafana
- Datadog
- New Relic
- Application Insights

### Logging

**Structured Logging:**
```python
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s'
)
```

**Log Aggregation:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Loki + Grafana
- CloudWatch (AWS)
- Azure Monitor

### Health Checks

Monitor these endpoints:
- `GET /health` - Application health
- `GET /api/admin/health` - Detailed system health

## Security Hardening

### 1. Change Default Credentials

```bash
docker-compose exec backend python scripts/create_admin.py
# Follow prompts to create new admin user
```

### 2. SSL/TLS Configuration

- Use Let's Encrypt for free SSL certificates
- Configure HTTPS redirect
- Enable HSTS headers
- Use strong cipher suites

### 3. Firewall Rules

- Only expose ports 80 and 443
- Restrict database access to internal network
- Use security groups (AWS) or firewall rules

### 4. API Security

- Rate limiting (implement in nginx or application)
- Input validation and sanitization
- SQL injection prevention (using ORM)
- XSS protection (React handles this)
- CSRF protection for state-changing operations

### 5. Container Security

- Use non-root users in containers
- Regularly update base images
- Scan images for vulnerabilities
- Use secrets management (Docker secrets, AWS Secrets Manager)

## Backup Procedures

### Database Backups

**Automated Daily Backups:**
```bash
#!/bin/bash
# backup-db.sh
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U user aigov > backup_$DATE.sql
# Upload to S3 or backup storage
aws s3 cp backup_$DATE.sql s3://your-backup-bucket/
```

**Schedule with cron:**
```bash
0 2 * * * /path/to/backup-db.sh
```

### Qdrant Backups

- Qdrant Cloud: Automatic backups included
- Self-hosted: Snapshot volumes regularly
- Export collections periodically

### Application Data

- Backup uploaded documents
- Backup configuration files
- Version control for code changes

### Recovery Procedures

1. **Database Recovery:**
   ```bash
   docker-compose exec -T postgres psql -U user aigov < backup_YYYYMMDD.sql
   ```

2. **Full System Recovery:**
   - Restore database
   - Restore Qdrant data
   - Redeploy containers
   - Verify health endpoints

## Troubleshooting

### Common Issues

**High Memory Usage:**
- Reduce number of workers
- Implement caching
- Optimize database queries
- Scale horizontally

**Slow Query Responses:**
- Check Qdrant performance
- Optimize database indexes
- Implement caching
- Review embedding model performance

**Connection Errors:**
- Check network configuration
- Verify environment variables
- Review firewall rules
- Check service health

### Performance Tuning

**Backend:**
- Adjust uvicorn workers: `--workers 4`
- Enable connection pooling
- Optimize database queries
- Use async operations where possible

**Frontend:**
- Enable gzip compression
- Optimize bundle size
- Use CDN for static assets
- Implement lazy loading

**Database:**
- Create appropriate indexes
- Regular VACUUM and ANALYZE
- Tune PostgreSQL configuration
- Monitor slow queries

## Support

For production issues:
1. Check application logs
2. Review health endpoints
3. Monitor system metrics
4. Consult this deployment guide

