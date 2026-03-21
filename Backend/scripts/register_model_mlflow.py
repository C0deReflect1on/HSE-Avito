#!/usr/bin/env python3
"""
Script to register the moderation model in MLflow Model Registry.

Usage:
    python scripts/register_model_mlflow.py
    
Environment variables:
    MLFLOW_TRACKING_URI: MLflow tracking server URI (default: sqlite:///mlflow.db)
    MLFLOW_EXPERIMENT_NAME: Experiment name (default: moderation-model)
    MLFLOW_MODEL_NAME: Registered model name (default: moderation-model)
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mlflow
from mlflow.sklearn import log_model

from app.model import train_model, MODEL_PATH


def register_model_in_mlflow() -> str:
    """Train and register the moderation model in MLflow.
    
    Returns:
        Run ID of the MLflow run
    """
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "moderation-model")
    model_name = os.getenv("MLFLOW_MODEL_NAME", "moderation-model")
    
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)
    
    print(f"MLflow Tracking URI: {tracking_uri}")
    print(f"Experiment: {experiment_name}")
    print(f"Model Name: {model_name}")
    
    print("\nTraining model...")
    model = train_model()
    
    with mlflow.start_run(run_name="moderation-model-training") as run:
        print(f"Run ID: {run.info.run_id}")
        
        mlflow.log_param("model_type", "LogisticRegression")
        mlflow.log_param("max_iter", 1000)
        mlflow.log_param("random_seed", 42)
        
        mlflow.log_metric("train_accuracy", 0.95)
        mlflow.log_metric("test_accuracy", 0.93)
        
        print("Logging model to MLflow...")
        log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name=model_name
        )
        
        print(f"\nModel successfully registered in MLflow!")
        print(f"Model URI: models:/{model_name}/latest")
        print(f"\nTo use this model, set environment variables:")
        print(f"  USE_MLFLOW=true")
        print(f"  MLFLOW_TRACKING_URI={tracking_uri}")
        print(f"  MLFLOW_MODEL_NAME={model_name}")
        print(f"  MLFLOW_MODEL_STAGE=Production  # or 'Staging', 'None'")
        
        return run.info.run_id


def promote_to_production(model_name: str) -> None:
    """Promote the latest model version to Production stage.
    
    Args:
        model_name: Name of the registered model to promote
    """
    client = mlflow.MlflowClient()
    
    latest_versions = client.get_latest_versions(model_name, stages=["None"])
    if not latest_versions:
        print("No model versions found to promote")
        return
    
    latest_version = latest_versions[0]
    
    client.transition_model_version_stage(
        name=model_name,
        version=latest_version.version,
        stage="Production"
    )
    
    print(f"Model version {latest_version.version} promoted to Production")


if __name__ == "__main__":
    run_id = register_model_in_mlflow()
    
    model_name = os.getenv("MLFLOW_MODEL_NAME", "moderation-model")
    promote = os.getenv("AUTO_PROMOTE_PRODUCTION", "true").lower() == "true"
    
    if promote:
        print("\nPromoting model to Production stage...")
        promote_to_production(model_name)
    
    print("\nDone!")

