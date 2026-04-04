# Changelog

All notable changes to ENGCAD Automação will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Rate limiting middleware with configurable limits
- Security verification endpoint `/api/security/check`

## [2.5.0] - 2025-01-29

### Added

- **FASE 1 - Infraestrutura Crítica**
  - pytest test structure with 68 unit tests across 4 test files
  - PostgreSQL production configuration with connection pooling
  - Alembic database migrations (9 tables + AI fields)
  - Test fixtures for authentication, database, and API client

- **FASE 2 - Performance & DevOps**
  - LRU/Redis hybrid cache system (`backend/cache.py`)
  - MockAutoCADDriver for development without AutoCAD installed
  - Enhanced CI/CD pipeline with pytest, linting, and security scans
  - Code coverage reporting with Codecov integration

- **FASE 3 - Security & Documentation**
  - Security headers middleware (CSP, HSTS, X-Frame-Options, etc.)
  - Secure CORS configuration with environment-based origins
  - CHANGELOG.md for version tracking

### Changed

- Updated TypeScript config to ES2020 with bundler module resolution
- Improved CI/CD workflow with Ubuntu-based testing and Windows quality checks
- Enhanced error handling in CAM routes with proper status codes

### Fixed

- Python 3.14 compatibility issues with ezdxf import
- Deprecated `datetime.utcnow()` replaced with `datetime.now(UTC)`
- Alembic migration chain (002 properly references 001)

## [2.4.0] - 2025-01-28

### Added

- **10 Plasma CNC Improvements**
  1. G-code HAFCO compatibility (Australian/NZ cutting machines)
  2. Automatic lead-in/lead-out with pierce point optimization
  3. Multi-torch support (2-4 simultaneous torches)
  4. Intelligent kerf compensation based on material/thickness
  5. Collision detection with path optimization
  6. Predictive maintenance with cut hour tracking
  7. DXF/SVG to G-code batch conversion
  8. Real-time feed rate optimization
  9. Part nesting with rotation/mirroring
  10. Enhanced quality classification (A/B/C grades)

### Changed

- Improved plasma optimizer with machine-specific parameters
- Enhanced nesting engine with better material utilization

## [2.3.0] - 2025-01-27

### Added

- AI-powered drawing analyzer
- Pipe routing optimization engine
- Cost estimator with material breakdown
- Document generator (BOM, specifications)
- Conflict detector for pipe intersections

### Changed

- Migrated AI engines to modular architecture
- Improved error handling across all endpoints

## [2.2.0] - 2025-01-15

### Added

- CAM module for CNC integration
- G-code generator with post-processor support
- DXF export functionality
- Toolpath optimization algorithms

### Fixed

- Memory leaks in long-running sessions
- WebSocket reconnection stability

## [2.1.0] - 2025-01-01

### Added

- Enterprise license management
- Multi-tenant support
- Audit trail logging
- Notification system with webhooks

### Security

- JWT token refresh mechanism
- API key authentication option
- Input validation hardening

## [2.0.0] - 2024-12-15

### Added

- Complete backend rewrite with FastAPI
- React frontend with TypeScript
- Real-time AutoCAD synchronization
- WebSocket communication layer

### Changed

- Architecture migrated to microservices pattern
- Database schema redesigned for scalability

### Removed

- Legacy Flask backend
- jQuery-based frontend

## [1.0.0] - 2024-10-01

### Added

- Initial release
- Basic AutoCAD automation
- Pipe drawing tools
- Component insertion
- Layer management
- Export to DXF/PDF

---

## Version History Summary

| Version | Date       | Highlights                          |
| ------- | ---------- | ----------------------------------- |
| 2.5.0   | 2025-01-29 | Full system optimization (FASE 1-3) |
| 2.4.0   | 2025-01-28 | 10 Plasma CNC improvements          |
| 2.3.0   | 2025-01-27 | AI engines integration              |
| 2.2.0   | 2025-01-15 | CAM module launch                   |
| 2.1.0   | 2025-01-01 | Enterprise features                 |
| 2.0.0   | 2024-12-15 | Major rewrite (FastAPI + React)     |
| 1.0.0   | 2024-10-01 | Initial release                     |

---

## Migration Notes

### Upgrading to 2.5.0

1. **Database Migration**

   ```bash
   # Run Alembic migrations
   alembic upgrade head
   ```

2. **Environment Variables**

   ```bash
   # New optional variables
   MOCK_AUTOCAD=1          # Enable AutoCAD mock for development
   REDIS_URL=redis://...   # Optional Redis for distributed caching
   SECURITY_CSP_DISABLED=0 # Enable Content-Security-Policy
   ```

3. **Dependencies**
   ```bash
   pip install pytest pytest-cov pytest-asyncio
   ```

### Upgrading to 2.0.0

Major breaking changes - see full migration guide in `docs/MIGRATION_2.0.md`.

---

## Links

- [Documentation](./docs/README.md)
- [API Reference](./docs/API_REFERENCE.md)
- [Contributing](./CONTRIBUTING.md)
- [Security Policy](./SECURITY.md)
