# Custom Wake Word Training Guide for OpenWakeWord

This guide will help you train custom wake words like "Hey Assistant" for your Voice Assistant using OpenWakeWord - **completely free, no API keys required!**

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Google Colab)](#quick-start-google-colab)
3. [Local Training Setup](#local-training-setup)
4. [Step-by-Step Training Process](#step-by-step-training-process)
5. [Using Custom Models](#using-custom-models)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Google Account** (for Google Colab - easiest method)
- **OR Python 3.8+** (for local training)
- **No paid API keys required!** 🎉

---

## Quick Start (Google Colab)

The **fastest and easiest** way to train your custom wake word is using Google Colab's free GPUs.

### Step 1: Access the Training Notebook

1. Open the [OpenWakeWord Training Notebook](https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb)
2. Sign in with your Google account
3. Click **Runtime** → **Change runtime type** → Select **GPU** (T4)

### Step 2: Generate Training Data

```python
# In the Colab notebook, configure your wake word
WAKE_WORD = "hey assistant"  # Your custom phrase
NUM_SAMPLES = 1000  # More samples = better accuracy

# The notebook will automatically generate synthetic training data
# using text-to-speech models (no manual recording needed!)
```

### Step 3: Train the Model

```python
# Run all cells in the notebook
# Training takes approximately 30-60 minutes on Google Colab GPU
# You'll get a .onnx or .tflite model file when done
```

### Step 4: Download Your Model

After training completes:
1. Download the generated `.onnx` file (e.g., `hey_assistant.onnx`)
2. Place it in your project: `D:\Voice_Assistant\models\wake_word\`

---

## Local Training Setup

If you prefer training locally (requires more setup):

### Installation

```bash
# Clone OpenWakeWord repository
git clone https://github.com/dscripka/openWakeWord.git
cd openWakeWord

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements_training.txt
```

### Generate Training Data

```bash
# Generate synthetic training data for your wake word
python openwakeword/generate_training_data.py \
    --wake_word "hey assistant" \
    --output_dir data/hey_assistant \
    --num_samples 1000
```

### Train the Model

```bash
# Train custom model (takes 1-2 hours on CPU, 30-60 min on GPU)
python openwakeword/train.py \
    --data_dir data/hey_assistant \
    --output_dir models/hey_assistant \
    --wake_word "hey assistant" \
    --epochs 50
```

---

## Step-by-Step Training Process

### Phase 1: Data Generation (Synthetic Speech)

OpenWakeWord uses **100% synthetic speech** generated from TTS models. No manual recording required!

**Advantages:**
- ✅ No need to record thousands of samples manually
- ✅ Automatic variation in:
  - Speaker voices (male, female, different accents)
  - Speaking speeds
  - Background noise levels
  - Acoustic environments

**Process:**
1. Text-to-speech models generate audio for your wake word
2. Variations are automatically created (different voices, speeds, pitches)
3. Background noise and room acoustics are simulated
4. Negative samples (non-wake-word audio) are generated

### Phase 2: Model Training

The system trains a neural network to detect your wake word in real-time audio streams.

**Model Architecture:**
- Input: 80ms audio frames (16kHz)
- Output: Confidence score (0.0 to 1.0)
- Optimized for: Low latency, high accuracy, low CPU usage

**Training Metrics to Monitor:**
- **Accuracy**: Should reach >95% on validation set
- **False Accept Rate (FAR)**: <1% (how often it triggers incorrectly)
- **False Reject Rate (FRR)**: <5% (how often it misses the wake word)

### Phase 3: Model Export

The trained model is exported in ONNX format for cross-platform compatibility.

---

## Using Custom Models

### Method 1: Configure in `assistant_config.yaml`

```yaml
wake_word:
  library: "openwakeword"
  sensitivity: 0.5
  model_path: "models/wake_word/"
  models:
    - "alexa"  # Built-in model
    - "hey_assistant"  # Your custom model (without .onnx extension)
```

### Method 2: Programmatically Add Custom Model

```python
from src.services.wake_word import WakeWordDetector
from src.core.config import get_config

config = get_config()
detector = WakeWordDetector(config, logger, audio_utils)
detector.initialize()

# Add your custom model
detector.add_custom_model("models/wake_word/hey_assistant.onnx")

# Start detection
detector.start()
```

### Method 3: Python Script for Testing

```python
import openwakeword
from openwakeword.model import Model

# Load your custom model
model = Model(
    wakeword_models=["hey_assistant"],  # Looks in default model directory
    inference_framework='onnx'
)

# Or specify full path
model = Model(
    custom_verifier_models={
        "D:/Voice_Assistant/models/wake_word/hey_assistant.onnx": 0.5
    },
    inference_framework='onnx'
)

# Test with audio
import sounddevice as sd
import numpy as np

SAMPLE_RATE = 16000
CHUNK_SIZE = 1280  # 80ms

stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, blocksize=CHUNK_SIZE)
stream.start()

print("Listening for 'hey assistant'...")
while True:
    audio, _ = stream.read(CHUNK_SIZE)
    audio = audio.flatten().astype(np.int16)

    prediction = model.predict(audio)

    for wake_word, score in prediction.items():
        if score > 0.5:
            print(f"🎯 Wake word detected! Confidence: {score:.2f}")
```

---

## Advanced Configuration

### Adjusting Sensitivity

```python
# In your config
wake_word:
  sensitivity: 0.5  # Default
  # Lower = fewer false positives, may miss some detections
  # Higher = catches more detections, may have false positives

# Recommended values:
# - 0.3-0.4: Very strict (noisy environments)
# - 0.5: Balanced (default)
# - 0.6-0.7: More sensitive (quiet environments)
```

### Multiple Wake Words

You can use multiple wake words simultaneously:

```python
models = ["hey_assistant", "alexa", "hey_jarvis"]
```

The detector will trigger on any of them.

### Performance Optimization

```python
# Use ONNX Runtime for best performance
model = Model(
    wakeword_models=["hey_assistant"],
    inference_framework='onnx'  # Faster than TFLite
)

# CPU optimization
import openwakeword
openwakeword.utils.set_num_threads(4)  # Use 4 CPU threads
```

---

## Training Tips for Best Results

### 1. **Choose a Good Wake Word**

✅ Good wake words:
- **3-4 syllables**: "Hey Assistant", "Hey Jarvis"
- **Distinct phonemes**: Avoid common words
- **Clear pronunciation**: Easy to say consistently

❌ Avoid:
- Too short: "Hey", "Hi" (too many false positives)
- Too long: "Hey Computer Assistant Please" (hard to trigger)
- Common words: "Computer", "System" (frequent false positives)

### 2. **Increase Training Samples**

```python
# More samples = better accuracy
NUM_SAMPLES = 2000  # Instead of 1000 (default)
```

**Recommended:**
- Basic accuracy: 1,000 samples
- Good accuracy: 2,000 samples
- Excellent accuracy: 5,000+ samples

### 3. **Add Background Noise**

```python
# In the training notebook
BACKGROUND_NOISE_LEVEL = 0.3  # 0.0 to 1.0
```

This helps the model work in noisy environments.

### 4. **Test in Real Conditions**

After training, test your model:
- In quiet rooms
- With background noise (TV, music, fans)
- From different distances
- With different speaking speeds

---

## Troubleshooting

### Issue: Model not detecting wake word

**Solutions:**
1. **Lower sensitivity threshold**:
   ```python
   wake_word.sensitivity = 0.3  # Instead of 0.5
   ```

2. **Retrain with more samples**:
   ```python
   NUM_SAMPLES = 3000  # Increase from 1000
   ```

3. **Check microphone setup**:
   ```bash
   python -c "import sounddevice; print(sounddevice.query_devices())"
   ```

### Issue: Too many false positives

**Solutions:**
1. **Raise sensitivity threshold**:
   ```python
   wake_word.sensitivity = 0.7  # Instead of 0.5
   ```

2. **Choose a more distinct wake word**

3. **Add more negative samples** during training

### Issue: Training fails in Google Colab

**Solutions:**
1. Check GPU is enabled: **Runtime** → **Change runtime type** → **GPU**
2. Restart runtime: **Runtime** → **Restart runtime**
3. Reduce training samples if out of memory:
   ```python
   NUM_SAMPLES = 500  # Reduce if needed
   ```

### Issue: Model file not loading

**Solutions:**
1. Verify file path is correct
2. Check file extension matches:
   ```python
   # Config references without extension
   models: ["hey_assistant"]  # NOT "hey_assistant.onnx"

   # File should be named:
   # models/wake_word/hey_assistant.onnx
   ```

3. Ensure ONNX runtime is installed:
   ```bash
   pip install onnxruntime
   ```

---

## Resources

- **OpenWakeWord GitHub**: https://github.com/dscripka/openWakeWord
- **Training Notebook**: [Google Colab Link](https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb)
- **Pre-trained Models**: Available in OpenWakeWord repository
- **Community Forum**: https://community.rhasspy.org/c/openwakeword

---

## Next Steps

1. ✅ Train your first custom wake word using Google Colab
2. ✅ Test it in your Voice Assistant
3. ✅ Adjust sensitivity for your environment
4. ✅ Train additional wake words for different use cases

**Congratulations!** You now have a completely free, open-source wake word detection system with no API keys required! 🎉

---

## Example: Complete Setup Script

```bash
# 1. Install openwakeword
pip install openwakeword>=0.6.0

# 2. Create model directory
mkdir -p models/wake_word

# 3. Download your trained model
# (After training in Google Colab, download hey_assistant.onnx)
# Place it in: models/wake_word/hey_assistant.onnx

# 4. Update config
cat >> config/assistant_config.yaml << EOF
wake_word:
  library: "openwakeword"
  sensitivity: 0.5
  model_path: "models/wake_word/"
  models:
    - "hey_assistant"
EOF

# 5. Test it!
python -m src.cli.assistant
```

**Say "Hey Assistant" and watch the magic happen!** ✨
