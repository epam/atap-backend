# Accessibility Checker:

## Application configuration
#### Application Start (Local development)

```bash
docker-compose -f docker-compose-dev.yml -f docker-compose.yml up -d
```
And open `http://localhost:8000`



# Sentry local configuration:

#### Generate secret key

```bash
docker-compose -f docker-compose-sentry.yml run --rm sentry-base config generate-secret-key
```

And then set generated key to `SENTRY_SECRET_KEY` in `.env`.

#### Initialize database

If this is a new database, you'll need to run `upgrade`.

```bash
docker-compose -f docker-compose-sentry.yml run --rm sentry-base upgrade
```

And **create** an initial user, if you need.


#### Service Start 

```bash
docker-compose -f docker-compose-sentry.yml up -d
```

And open `http://localhost:9000`
