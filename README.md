# Ethereum Sepolia Faucet API

A Django REST API service that provides a faucet for Sepolia testnet ETH. The service allows users to request small amounts of test ETH with built-in rate limiting and transaction tracking.
Source of funds is from a pre-funded wallet.

## Features

- Request Sepolia ETH (configurable amount, default: 0.0001 ETH)
- Rate limiting by IP address and wallet address
- Transaction tracking and 24-hour statistics
- Dockerized application with PostgreSQL database
- Configurable via environment variables
- Tested with Sepolia testnet

## Prerequisites

- Docker and Docker Compose
- Python 3.11+
- A wallet with Sepolia ETH
- Infura account or other Ethereum node provider

## Configuration
Create a `.env` file in the root directory:

```
# Ethereum node configuration
ETHEREUM_NODE_URL=https://sepolia.infura.io/v3/your-project-id
CHAIN_ID=11155111

# Faucet configuration
FAUCET_AMOUNT=0.0001
FAUCET_INTERVAL_MIN=1

# Private key and public address for the faucet account
PRIVATE_KEY=your-private-key
PUBLIC_ADDRESS=your-public-address

# Database configuration
POSTGRES_DB=faucet
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

## Running with Docker

Build and start the containers (it will also run migrations):
```bash
make docker-up
```

The API will be available at `http://localhost:8000`

## Running Locally

1. Start the PostgreSQL database:
```bash
make db-up
```

2. Create and activate a virtual environment:
```bash
make venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
make install
```

4. Run migrations and development server:
```bash
make run
```

To stop the database:
```bash
make db-down
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Request Funds (POST /faucet/fund/)

Request Sepolia ETH to be sent to your wallet.

**Request:**
```
curl -X POST http://localhost:8000/faucet/fund/ \
-H "Content-Type: application/json" \
-d '{"wallet_address": "0x9F184A0c66EEe3fAe5DeeAc5cd741B6D63652848"}'   
```

**Response:**
```
{"transaction_hash": "0x1234567890abcdef"}
```

### 2. Get Statistics (GET /faucet/stats/)

Get the number of successful and failed transactions in the last 24 hours.

**Request:**
```
curl http://localhost:8000/faucet/stats/
```
**Response:**
```
{"total_transactions":1,"last_24h_transactions":1,"successful_transactions":1,"failed_transactions":0}
```

## Running Tests

### With Docker:
```                 
docker-compose exec web python manage.py test or docker-compose exec web shell make test
```

### Locally:
```
make test or pytest
```


