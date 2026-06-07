import numpy as np

def generate_data(duration=10, samples=2000):
    t = np.linspace(0, duration, samples)

    voltage = 600 + 5 * np.random.randn(samples)   # DC Bus
    frequency = 50 + 0.02 * np.random.randn(samples)
    current = 10 + 0.5 * np.random.randn(samples)

    # Anomali (islanding / fault)
    start = samples // 2

    voltage[start:] = 560 + 10 * np.random.randn(samples - start)
    frequency[start:] = 48.8 + 0.2 * np.random.randn(samples - start)
    current[start:] = 15 + 2 * np.random.randn(samples - start)

    return t, voltage, frequency, current