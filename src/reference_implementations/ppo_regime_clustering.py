"""
SOURCE: git repos/Fiduciary-Sentinel-Core - Copy/rl_brain/regime_clustering.py
PURPOSE: Market regime detection using autoencoder + K-Means clustering.
         Used as auxiliary loss in DualHeadPPO training.
         Our PPO agent (src/drl/ppo_agent.py) can optionally use this.

RegimeManager:
- Trains a neural autoencoder on 21-dim state vectors
- Clusters latent space into 12 market regimes (trending, ranging, volatile, etc.)
- Provides predict_clusters() for labeling states during PPO training
- Supports incremental learning (partial_fit_regime) for live adaptation
"""

import torch
import torch.nn as nn
from sklearn.cluster import MiniBatchKMeans
import numpy as np
import pickle
import os


class RegimeAutoencoder(nn.Module):
    """
    Autoencoder that compresses 21-dim market state into 12-dim latent regime space.
    Architecture: 21 → 80 → 128 → 64 → 32 → 12 (encoder)
                  12 → 32 → 64 → 128 → 80 → 21 (decoder)
    """
    def __init__(self, input_dim=21, latent_dim=12):
        super(RegimeAutoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 80), nn.ReLU(),
            nn.Linear(80, 128), nn.ReLU(),
            nn.Linear(128, 64), nn.ReLU(),
            nn.Linear(64, 32), nn.ReLU(),
            nn.Linear(32, latent_dim)
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32), nn.ReLU(),
            nn.Linear(32, 64), nn.ReLU(),
            nn.Linear(64, 128), nn.ReLU(),
            nn.Linear(128, 80), nn.ReLU(),
            nn.Linear(80, input_dim)
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))

    def get_features(self, x):
        return self.encoder(x)


class RegimeManager:
    """
    Manages market regime detection for the PPO agent's auxiliary loss.

    Usage:
        manager = RegimeManager()
        manager.train_regime_models(historical_states)  # one-time training
        labels = manager.predict_clusters(current_states)  # during PPO training
    """
    def __init__(self, input_dim=21, n_clusters=12, model_dir="data/models/"):
        self.ae = RegimeAutoencoder(input_dim=input_dim, latent_dim=n_clusters)
        self.kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
        self.n_clusters = n_clusters
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self.is_trained = False

    def train_regime_models(self, states, epochs=50, batch_size=256, lr=1e-3):
        """Pre-train Autoencoder and KMeans on a dataset of states."""
        optimizer = torch.optim.Adam(self.ae.parameters(), lr=lr)
        criterion = nn.MSELoss()
        dataset = torch.tensor(states, dtype=torch.float32)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

        for epoch in range(epochs):
            total_loss = 0
            for batch in dataloader:
                optimizer.zero_grad()
                loss = criterion(self.ae(batch), batch)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            if (epoch + 1) % 10 == 0:
                print(f"[REGIME] Epoch {epoch+1}/{epochs} | Loss: {total_loss/len(dataloader):.4f}")

        with torch.no_grad():
            self.ae.eval()
            latent = self.ae.get_features(dataset).numpy()
        self.kmeans.fit(latent)

        torch.save(self.ae.state_dict(), os.path.join(self.model_dir, "autoencoder.pth"))
        with open(os.path.join(self.model_dir, "kmeans.pkl"), "wb") as f:
            pickle.dump(self.kmeans, f)
        self.is_trained = True

    def partial_fit_regime(self, states, lr=1e-4):
        """Incremental learning on live data stream."""
        if not self.is_trained and not self.load_models():
            return
        optimizer = torch.optim.Adam(self.ae.parameters(), lr=lr)
        criterion = nn.MSELoss()
        tensor_states = torch.tensor(states, dtype=torch.float32)
        self.ae.train()
        optimizer.zero_grad()
        loss = criterion(self.ae(tensor_states), tensor_states)
        loss.backward()
        optimizer.step()
        with torch.no_grad():
            self.ae.eval()
            latent = self.ae.get_features(tensor_states).numpy()
        self.kmeans.partial_fit(latent)
        torch.save(self.ae.state_dict(), os.path.join(self.model_dir, "autoencoder.pth"))
        with open(os.path.join(self.model_dir, "kmeans.pkl"), "wb") as f:
            pickle.dump(self.kmeans, f)

    def load_models(self):
        ae_path = os.path.join(self.model_dir, "autoencoder.pth")
        km_path = os.path.join(self.model_dir, "kmeans.pkl")
        if os.path.exists(ae_path) and os.path.exists(km_path):
            self.ae.load_state_dict(torch.load(ae_path))
            self.ae.eval()
            with open(km_path, "rb") as f:
                self.kmeans = pickle.load(f)
            self.is_trained = True
            return True
        return False

    def predict_clusters(self, states) -> np.ndarray:
        """Return cluster labels for a batch of state vectors."""
        if not self.is_trained and not self.load_models():
            raise RuntimeError("Regime models not trained.")
        with torch.no_grad():
            z = self.ae.get_features(torch.tensor(states, dtype=torch.float32)).numpy()
        return self.kmeans.predict(z)
