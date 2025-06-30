import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import json
import os
from datetime import datetime, timedelta
import psutil
from sqlalchemy import create_engine
import logging
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedPipelineLoadPredictor:
    def __init__(self, model_type='ensemble'):
        """  
        Initialiseur avec choix de modèle
        model_type: 'rf', 'gb', 'ensemble', 'linear'
        """
        self.model_type = model_type
        self.models = self._initialize_models()
        self.best_model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.is_trained = False
        self.feature_importance = None
        self.training_history = []
        
        # Chemins cross-platform
        self.model_dir = Path('models')
        self.model_dir.mkdir(exist_ok=True)
        
    def _initialize_models(self):
        """Initialise différents modèles pour comparaison"""
        return {
            'rf': RandomForestRegressor(
                n_estimators=200,
                max_depth=15,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            ),
            'gb': GradientBoostingRegressor(
                n_estimators=150,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            ),
            'linear': LinearRegression()
        }
    
    def collect_current_metrics(self):
        """Collecte les métriques système enrichies"""
        now = datetime.now()
        
        # Métriques système de base
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Métriques réseau
        net_io = psutil.net_io_counters()
        
        # Métriques de processus
        process_count = len(psutil.pids())
        
        return {
            # Temporelles
            'hour': now.hour,
            'day_of_week': now.weekday(),
            'day_of_month': now.day,
            'month': now.month,
            'is_weekend': 1 if now.weekday() >= 5 else 0,
            'is_business_hours': 1 if 8 <= now.hour <= 18 else 0,
            
            # Système
            'cpu_usage': cpu_percent,
            'memory_usage': memory.percent,
            'memory_available_gb': memory.available / (1024**3),
            'disk_usage_percent': disk.percent,
            'disk_free_gb': disk.free / (1024**3),
            
            # Processus et réseau
            'process_count': process_count,
            'network_bytes_sent': net_io.bytes_sent,
            'network_bytes_recv': net_io.bytes_recv,
            'network_packets_sent': net_io.packets_sent,
            'network_packets_recv': net_io.packets_recv,
            
            # Features dérivées
            'cpu_memory_ratio': cpu_percent / max(memory.percent, 1),
            'load_indicator': (cpu_percent * memory.percent) / 100,
        }
    
    def engineer_features(self, data):
        """Feature engineering avancé"""
        df = data.copy()
        
        # Features cycliques pour les heures
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        # Features cycliques pour les jours
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        # Features d'interaction
        df['cpu_memory_interaction'] = df['cpu_usage'] * df['memory_usage']
        df['network_total'] = df['network_bytes_sent'] + df['network_bytes_recv']
        
        # Features de moyenne mobile (si suffisamment de données)
        if len(df) > 5:
            df['cpu_rolling_mean'] = df['cpu_usage'].rolling(window=3, min_periods=1).mean()
            df['memory_rolling_mean'] = df['memory_usage'].rolling(window=3, min_periods=1).mean()
        else:
            df['cpu_rolling_mean'] = df['cpu_usage']
            df['memory_rolling_mean'] = df['memory_usage']
        
        return df
    
    def prepare_features(self, data):
        """Sélection et préparation des features optimisées"""
        features = [
            # Temporelles
            'hour_sin', 'hour_cos', 'day_sin', 'day_cos',
            'is_weekend', 'is_business_hours',
            
            # Système
            'cpu_usage', 'memory_usage', 'disk_usage_percent',
            'process_count', 'load_indicator',
            
            # Réseau
            'network_total',
            
            # Dérivées
            'cpu_memory_interaction', 'cpu_rolling_mean', 'memory_rolling_mean'
        ]
        
        return data[features]
    
    def optimize_hyperparameters(self, X_train, y_train):
        """Optimisation des hyperparamètres avec GridSearch"""
        param_grids = {
            'rf': {
                'n_estimators': [100, 200],
                'max_depth': [10, 15, 20],
                'min_samples_split': [2, 5],
                'min_samples_leaf': [1, 2]
            },
            'gb': {
                'n_estimators': [100, 150],
                'learning_rate': [0.05, 0.1, 0.15],
                'max_depth': [4, 6, 8]
            }
        }
        
        best_models = {}
        
        for model_name, model in self.models.items():
            if model_name in param_grids:
                logger.info(f"Optimisation des hyperparamètres pour {model_name}...")
                grid_search = GridSearchCV(
                    model, param_grids[model_name],
                    cv=3, scoring='neg_mean_squared_error',
                    n_jobs=-1, verbose=0
                )
                grid_search.fit(X_train, y_train)
                best_models[model_name] = grid_search.best_estimator_
                logger.info(f"Meilleurs paramètres {model_name}: {grid_search.best_params_}")
            else:
                model.fit(X_train, y_train)
                best_models[model_name] = model
        
        return best_models
    
    def train_model(self, historical_data, optimize_params=True):
        """Entraînement amélioré avec validation croisée"""
        if len(historical_data) < 20:
            logger.warning("Pas assez de données pour un entraînement robuste (minimum 20)")
            return False
        
        try:
            # Feature engineering
            data_engineered = self.engineer_features(historical_data)
            
            # Préparation des features
            X = self.prepare_features(data_engineered)
            y = historical_data['duration_seconds']
            
            # Nettoyage des outliers (IQR method)
            Q1 = y.quantile(0.25)
            Q3 = y.quantile(0.75)
            IQR = Q3 - Q1
            y_clean = y[(y >= Q1 - 1.5 * IQR) & (y <= Q3 + 1.5 * IQR)]
            X_clean = X.loc[y_clean.index]
            
            logger.info(f"Données nettoyées: {len(y_clean)}/{len(y)} échantillons conservés")
            
            # Normalisation
            X_scaled = self.scaler.fit_transform(X_clean)
            
            # Division train/test
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y_clean, test_size=0.2, random_state=42, stratify=None
            )
            
            # Optimisation des hyperparamètres
            if optimize_params and len(X_train) > 50:
                optimized_models = self.optimize_hyperparameters(X_train, y_train)
                self.models.update(optimized_models)
            
            # Entraînement et évaluation de tous les modèles
            model_scores = {}
            
            for name, model in self.models.items():
                # Validation croisée
                cv_scores = cross_val_score(
                    model, X_train, y_train, 
                    cv=min(5, len(X_train)//4), 
                    scoring='neg_mean_squared_error'
                )
                
                # Entraînement final
                model.fit(X_train, y_train)
                
                # Évaluation sur le test set
                y_pred = model.predict(X_test)
                mse = mean_squared_error(y_test, y_pred)
                mae = mean_absolute_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                
                model_scores[name] = {
                    'cv_score': -cv_scores.mean(),
                    'cv_std': cv_scores.std(),
                    'test_mse': mse,
                    'test_mae': mae,
                    'test_r2': r2
                }
                
                logger.info(f"{name}: R² = {r2:.3f}, MAE = {mae:.1f}s, CV = {-cv_scores.mean():.3f}±{cv_scores.std():.3f}")
            
            # Sélection du meilleur modèle
            if self.model_type == 'ensemble':
                self.best_model = self._create_ensemble(X_train, y_train)
                logger.info("Modèle ensemble créé")
            else:
                best_model_name = min(model_scores.keys(), key=lambda x: model_scores[x]['test_mse'])
                self.best_model = self.models[best_model_name]
                logger.info(f"Meilleur modèle sélectionné: {best_model_name}")
            
            # Feature importance
            if hasattr(self.best_model, 'feature_importances_'):
                self.feature_importance = dict(zip(X.columns, self.best_model.feature_importances_))
                top_features = sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
                logger.info(f"Top 5 features: {top_features}")
            
            # Sauvegarde
            self._save_model()
            
            # Historique d'entraînement
            self.training_history.append({
                'timestamp': datetime.now(),
                'model_scores': model_scores,
                'n_samples': len(X_clean),
                'features': list(X.columns)
            })
            
            self.is_trained = True
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement: {e}")
            return False
    
    def _create_ensemble(self, X_train, y_train):
        """Crée un modèle ensemble pondéré"""
        from sklearn.ensemble import VotingRegressor
        
        # Sélection des modèles performants
        estimators = [
            ('rf', self.models['rf']),
            ('gb', self.models['gb'])
        ]
        
        ensemble = VotingRegressor(estimators=estimators)
        ensemble.fit(X_train, y_train)
        
        return ensemble
    
    def predict_pipeline_duration(self, target_hour=None, target_date=None):
        """Prédiction améliorée avec intervalles de confiance"""
        if not self.is_trained:
            if not self._load_model():
                logger.error("Aucun modèle entraîné disponible")
                return None
        
        try:
            current_metrics = self.collect_current_metrics()
            
            if target_hour is not None:
                current_metrics['hour'] = target_hour
                # Recalculer les features temporelles
                current_metrics['hour_sin'] = np.sin(2 * np.pi * target_hour / 24)
                current_metrics['hour_cos'] = np.cos(2 * np.pi * target_hour / 24)
                current_metrics['is_business_hours'] = 1 if 8 <= target_hour <= 18 else 0
            
            # Conversion et feature engineering
            df = pd.DataFrame([current_metrics])
            df_engineered = self.engineer_features(df)
            X = self.prepare_features(df_engineered)
            X_scaled = self.scaler.transform(X)
            
            # Prédiction
            prediction = self.best_model.predict(X_scaled)[0]
            
            # Calcul de l'intervalle de confiance
            confidence_interval = self._calculate_prediction_interval(X_scaled)
            
            return {
                'predicted_duration': max(0, prediction),  # Éviter les valeurs négatives
                'confidence_interval': confidence_interval,
                'optimal_time': self.find_optimal_execution_time(),
                'confidence_level': self._calculate_confidence(X_scaled),
                'timestamp': datetime.now(),
                'features_used': list(X.columns)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction: {e}")
            return None
    
    def _calculate_prediction_interval(self, X, confidence=0.95):
        """Calcule l'intervalle de prédiction"""
        if hasattr(self.best_model, 'estimators_'):
            # Pour les modèles ensemble
            predictions = np.array([tree.predict(X)[0] for tree in self.best_model.estimators_])
            mean_pred = np.mean(predictions)
            std_pred = np.std(predictions)
            
            # Intervalle basé sur la distribution des prédictions
            z_score = 1.96 if confidence == 0.95 else 2.58  # 99% confidence
            lower = mean_pred - z_score * std_pred
            upper = mean_pred + z_score * std_pred
            
            return {'lower': max(0, lower), 'upper': upper, 'std': std_pred}
        
        return {'lower': None, 'upper': None, 'std': None}
    
    def find_optimal_execution_time(self, look_ahead_hours=24):
        """Trouve le meilleur moment d'exécution sur les prochaines heures"""
        predictions = []
        
        for hour_offset in range(look_ahead_hours):
            target_time = datetime.now() + timedelta(hours=hour_offset)
            pred = self.predict_pipeline_duration(target_hour=target_time.hour)
            
            if pred:
                predictions.append({
                    'hour': target_time.hour,
                    'hour_offset': hour_offset,
                    'duration': pred['predicted_duration'],
                    'confidence': pred['confidence_level'],
                    'timestamp': target_time
                })
        
        if predictions:
            # Pondération par la confiance
            weighted_predictions = [
                {**p, 'weighted_duration': p['duration'] / max(p['confidence'], 0.1)}
                for p in predictions
            ]
            
            optimal = min(weighted_predictions, key=lambda x: x['weighted_duration'])
            return {
                'hour': optimal['hour'],
                'offset_hours': optimal['hour_offset'],
                'predicted_duration': optimal['duration'],
                'timestamp': optimal['timestamp']
            }
        
        return None
    
    def _calculate_confidence(self, X):
        """Calcule un score de confiance amélioré"""
        if hasattr(self.best_model, 'estimators_'):
            predictions = np.array([tree.predict(X)[0] for tree in self.best_model.estimators_])
            cv = np.std(predictions) / max(np.mean(predictions), 1)  # Coefficient de variation
            confidence = max(0, min(1, 1 - cv))
            return confidence
        
        return 0.8  # Confiance par défaut pour les modèles non-ensemble
    
    def _save_model(self):
        """Sauvegarde cross-platform"""
        try:
            joblib.dump(self.best_model, self.model_dir / 'ml_model.pkl')
            joblib.dump(self.scaler, self.model_dir / 'ml_scaler.pkl')
            
            # Sauvegarde des métadonnées
            metadata = {
                'model_type': self.model_type,
                'feature_importance': self.feature_importance,
                'training_history': self.training_history[-1] if self.training_history else None,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.model_dir / 'model_metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logger.info("Modèle sauvegardé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde: {e}")
    
    def _load_model(self):
        """Chargement cross-platform"""
        try:
            self.best_model = joblib.load(self.model_dir / 'ml_model.pkl')
            self.scaler = joblib.load(self.model_dir / 'ml_scaler.pkl')
            
            # Chargement des métadonnées
            metadata_path = self.model_dir / 'model_metadata.json'
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    self.feature_importance = metadata.get('feature_importance', {})
            
            self.is_trained = True
            logger.info("Modèle chargé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement: {e}")
            return False
    
    def get_model_diagnostics(self):
        """Diagnostics du modèle"""
        if not self.is_trained:
            return {"status": "not_trained"}
        
        return {
            "status": "trained",
            "model_type": self.model_type,
            "feature_importance": self.feature_importance,
            "training_history": self.training_history,
            "model_params": self.best_model.get_params() if hasattr(self.best_model, 'get_params') else None
        }

def enhanced_ml_pipeline_optimization():
    """Fonction optimisée pour Airflow"""
    
    try:
        # Connexion DB (avec gestion d'erreur)
        try:
            engine = create_engine('postgresql+psycopg2://admin:admin123@postgres:5432/mspr3')
        except:
            logger.warning("Connexion DB échouée, utilisation de données simulées")
            engine = None
        
        # Initialisation du prédicteur amélioré
        predictor = EnhancedPipelineLoadPredictor(model_type='ensemble')
        
        # Génération de données d'entraînement plus réalistes
        historical_data = generate_realistic_training_data()
        
        # Entraînement
        logger.info("Début de l'entraînement du modèle...")
        success = predictor.train_model(historical_data, optimize_params=True)
        
        if success:
            # Prédictions multiples
            current_prediction = predictor.predict_pipeline_duration()
            optimal_time = predictor.find_optimal_execution_time()
            
            if current_prediction:
                logger.info("🤖 PRÉDICTION ML AMÉLIORÉE:")
                logger.info(f"Durée prédite: {current_prediction['predicted_duration']:.1f}s")
                
                ci = current_prediction['confidence_interval']
                if ci['lower'] is not None:
                    logger.info(f"Intervalle confiance: [{ci['lower']:.1f}s - {ci['upper']:.1f}s]")
                
                logger.info(f"Confiance: {current_prediction['confidence_level']:.2f}")
                
                if optimal_time:
                    logger.info(f"Moment optimal: dans {optimal_time['offset_hours']}h ({optimal_time['hour']}h)")
                
                # Sauvegarde enrichie
                prediction_data = {
                    **current_prediction,
                    'optimal_execution': optimal_time,
                    'model_diagnostics': predictor.get_model_diagnostics()
                }
                
                with open(predictor.model_dir / 'ml_predictions.json', 'a') as f:
                    json.dump(prediction_data, f, default=str)
                    f.write('\n')
                
                # Alertes intelligentes
                threshold = 300  # 5 minutes
                if current_prediction['predicted_duration'] > threshold:
                    confidence = current_prediction['confidence_level']
                    if confidence > 0.7:
                        logger.warning("⚠️ ALERTE FORTE: Surcharge du pipeline prédite avec haute confiance!")
                        return "ALERT_HIGH_LOAD_CONFIDENT"
                    else:
                        logger.warning("⚠️ ALERTE MODÉRÉE: Surcharge possible (faible confiance)")
                        return "ALERT_HIGH_LOAD_UNCERTAIN"
                
                return "ML_SUCCESS_ENHANCED"
            
        else:
            logger.error("Échec de l'entraînement du modèle")
            return "ML_TRAINING_FAILED"
            
    except Exception as e:
        logger.error(f"Erreur dans le pipeline ML: {e}")
        return "ML_ERROR"

def generate_realistic_training_data(n_samples=500):
    """Génère des données d'entraînement plus réalistes"""
    np.random.seed(42)
    
    # Génération de base
    data = pd.DataFrame({
        'hour': np.random.randint(0, 24, n_samples),
        'day_of_week': np.random.randint(0, 7, n_samples),
        'day_of_month': np.random.randint(1, 29, n_samples),
        'month': np.random.randint(1, 13, n_samples),
    })
    
    # Features dérivées
    data['is_weekend'] = (data['day_of_week'] >= 5).astype(int)
    data['is_business_hours'] = ((data['hour'] >= 8) & (data['hour'] <= 18)).astype(int)
    
    # Métriques système avec patterns réalistes
    base_cpu = np.random.normal(25, 8, n_samples)
    base_memory = np.random.normal(40, 12, n_samples)
    
    # Ajout de patterns temporels
    # Business hours = plus de charge
    business_mask = data['is_business_hours'] == 1
    data.loc[business_mask, 'cpu_multiplier'] = np.random.uniform(1.2, 1.8, business_mask.sum())
    data.loc[~business_mask, 'cpu_multiplier'] = np.random.uniform(0.6, 1.0, (~business_mask).sum())
    
    # Weekend = moins de charge
    weekend_mask = data['is_weekend'] == 1
    data.loc[weekend_mask, 'weekend_multiplier'] = np.random.uniform(0.7, 1.0, weekend_mask.sum())
    data.loc[~weekend_mask, 'weekend_multiplier'] = np.random.uniform(1.0, 1.3, (~weekend_mask).sum())
    
    # Application des multipliers
    data['cpu_usage'] = np.clip(base_cpu * data['cpu_multiplier'] * data['weekend_multiplier'], 0, 100)
    data['memory_usage'] = np.clip(base_memory * data['cpu_multiplier'] * data['weekend_multiplier'], 0, 100)
    
    # Autres métriques
    data['disk_usage_percent'] = np.random.normal(60, 15, n_samples).clip(0, 100)
    data['process_count'] = np.random.randint(80, 200, n_samples)
    data['memory_available_gb'] = np.random.uniform(2, 16, n_samples)
    data['disk_free_gb'] = np.random.uniform(10, 100, n_samples)
    data['network_bytes_sent'] = np.random.randint(1000000, 50000000, n_samples)
    data['network_bytes_recv'] = np.random.randint(1000000, 50000000, n_samples)
    data['network_packets_sent'] = np.random.randint(1000, 10000, n_samples)
    data['network_packets_recv'] = np.random.randint(1000, 10000, n_samples)
    
    # Features dérivées
    data['cpu_memory_ratio'] = data['cpu_usage'] / np.maximum(data['memory_usage'], 1)
    data['load_indicator'] = (data['cpu_usage'] * data['memory_usage']) / 100
    
    # Variable cible avec relation complexe
    duration_base = 120  # 2 minutes de base
    
    # Impact des différents facteurs
    cpu_impact = data['cpu_usage'] * 1.5
    memory_impact = data['memory_usage'] * 1.2
    time_impact = np.where(data['is_business_hours'], 30, -20)
    weekend_impact = np.where(data['is_weekend'], -15, 10)
    load_impact = data['load_indicator'] * 0.8
    
    # Ajout de non-linéarités
    high_load_penalty = np.where(data['load_indicator'] > 50, 
                                 (data['load_indicator'] - 50) * 2, 0)
    
    data['duration_seconds'] = (duration_base + 
                               cpu_impact + memory_impact + 
                               time_impact + weekend_impact + 
                               load_impact + high_load_penalty +
                               np.random.normal(0, 20, n_samples))  # Bruit
    
    # Éviter les valeurs négatives
    data['duration_seconds'] = np.maximum(data['duration_seconds'], 30)
    
    # Nettoyage
    data = data.drop(['cpu_multiplier', 'weekend_multiplier'], axis=1)
    
    return data

if __name__ == "__main__":
    enhanced_ml_pipeline_optimization()