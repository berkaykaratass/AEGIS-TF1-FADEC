"""
PPO Recurrent Surge Predictor Training Script

Trains the SurgePredictor GRU policy network in the simulated turbofan environment
using Proximal Policy Optimization (PPO).
Saves trained weights to surge_weights.npz.

Copyright (c) 2026 AEGIS-TF1 Systems Development Group.
"""

import os
import numpy as np
from ai.models.surge_predictor import SurgePredictor, CompressorEnvironment

def train():
    print("Initializing Two-Spool Compressor Environment and Surge GRU Network...")
    env = CompressorEnvironment(dt=0.01)
    
    # 7 inputs, 16 hidden, 2 outputs, lr=0.002
    predictor = SurgePredictor(input_dim=7, hidden_dim=16, output_dim=2, lr=0.002)

    num_episodes = 500
    print(f"Beginning PPO Policy Gradient Training ({num_episodes} episodes)...")

    episode_rewards = []

    for ep in range(1, num_episodes + 1):
        state = env.reset()
        predictor.reset_hidden()

        states = []
        actions = []
        rewards = []
        log_probs = []
        values = []
        hidden_states = []

        done = False
        step_count = 0
        sigma = 0.5  # standard deviation of policy action distribution

        while not done:
            step_count += 1
            
            # Store current hidden state before step forward
            h_prev = predictor.h.copy()
            hidden_states.append(h_prev)

            # Forward pass: outputs [surge_prob, mean_fuel_adj]
            out, h_next, _, _, _ = predictor.forward_step(state, h_prev)
            
            # Sample continuous action from Gaussian policy: mean = out[1, 0]
            mean = out[1, 0]
            action = np.random.normal(mean, sigma)
            action = np.clip(action, -1.0, 1.0)  # Clip to valid control limits

            # Calculate log probability of the action
            log_prob = -0.5 * np.log(2.0 * np.pi * sigma**2) - ((action - mean)**2) / (2.0 * sigma**2)
            val = predictor.get_value(h_prev)

            # Step environment
            next_state, reward, done, _ = env.step(action)

            # Store experience
            states.append(state)
            actions.append(action)
            rewards.append(reward)
            log_probs.append(log_prob)
            values.append(val)

            # Move to next state and update hidden state
            state = next_state
            predictor.h = h_next

        # Compute discounted returns
        gamma = 0.99
        returns = []
        G = 0.0
        for r in reversed(rewards):
            G = r + gamma * G
            returns.insert(0, G)
        returns = np.array(returns)

        # Calculate advantages A_t = G_t - V(s_t)
        values = np.array(values)
        advantages = returns - values

        # Standardize advantages
        if len(advantages) > 1:
            std = np.std(advantages) + 1e-8
            advantages = (advantages - np.mean(advantages)) / std

        # Update weights using PPO actor-critic algorithm (BPTT through epoch)
        predictor.train_ppo_step(
            states=np.array(states),
            actions=np.array(actions),
            old_log_probs=np.array(log_probs),
            advantages=advantages,
            returns=returns,
            hs=np.array(hidden_states)
        )

        total_reward = sum(rewards)
        episode_rewards.append(total_reward)

        if ep % 50 == 0:
            avg_r = np.mean(episode_rewards[-50:])
            surged_status = "SURGED" if env.is_surged else "COMPLETED"
            print(f"Episode {ep:4d}/{num_episodes} | Avg Reward (last 50): {avg_r:7.2f} | Last Ep Status: {surged_status} | Steps: {step_count} | SM: {env.surge_margin:.4f} | Clearance: {env.delta_tip*1000:.3f} mm")

    print("Training completed.")
    
    # Save weights
    weights_path = "/Users/berkaykaratas/Downloads/turbojet/ai/models/surge_weights.npz"
    os.makedirs(os.path.dirname(weights_path), exist_ok=True)
    predictor.save_weights(weights_path)
    print(f"Trained weights saved to {weights_path}")

if __name__ == "__main__":
    train()
