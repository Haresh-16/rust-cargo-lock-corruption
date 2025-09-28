use anyhow::Result;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tokio::time::{sleep, Duration};
use tracing::{info, warn};
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize)]
struct Transaction {
    id: Uuid,
    amount: f64,
    currency: String,
    timestamp: DateTime<Utc>,
    status: TransactionStatus,
}

#[derive(Debug, Serialize, Deserialize)]
enum TransactionStatus {
    Pending,
    Completed,
    Failed,
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt::init();
    
    info!("Starting financial processor");
    
    let mut transactions = HashMap::new();
    
    // Create a test transaction
    let tx = Transaction {
        id: Uuid::new_v4(),
        amount: 100.50,
        currency: "USD".to_string(),
        timestamp: Utc::now(),
        status: TransactionStatus::Pending,
    };
    
    transactions.insert(tx.id, tx);
    
    // Simulate processing
    sleep(Duration::from_millis(100)).await;
    
    info!("Processed {} transactions", transactions.len());
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_transaction_creation() {
        let tx = Transaction {
            id: Uuid::new_v4(),
            amount: 50.0,
            currency: "EUR".to_string(),
            timestamp: Utc::now(),
            status: TransactionStatus::Pending,
        };
        
        assert_eq!(tx.amount, 50.0);
        assert_eq!(tx.currency, "EUR");
    }

    #[test]
    fn test_transaction_serialization() {
        let tx = Transaction {
            id: Uuid::new_v4(),
            amount: 75.25,
            currency: "GBP".to_string(),
            timestamp: Utc::now(),
            status: TransactionStatus::Completed,
        };
        
        let json = serde_json::to_string(&tx).unwrap();
        assert!(json.contains("75.25"));
        assert!(json.contains("GBP"));
    }

    #[tokio::test]
    async fn test_async_processing() {
        let start = std::time::Instant::now();
        sleep(Duration::from_millis(10)).await;
        let elapsed = start.elapsed();
        
        assert!(elapsed >= Duration::from_millis(10));
    }
}
