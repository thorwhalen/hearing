# **Architectural Frameworks and Comparative Analysis of Commercial and Open-Source Real-Time Meeting Transcription Pipelines**

The modern enterprise landscape requires seamless, secure, and low-latency systems to capture, transcribe, and analyze verbal communication. As organizations struggle with the operational costs of cloud-hosted transcription APIs and the data privacy concerns of sending sensitive conversations to third-party endpoints, two distinct design patterns have emerged. The first relies on commercial software-as-a-service platforms that provide polished, out-of-the-box transcription and summarization, albeit with restrictive free tiers and monetization chokepoints.1 The second embraces open-source, local-first architectures that execute speech-to-text and language modeling on-device, or orchestrate highly custom real-time voice pipelines via open-source frameworks.3 This report evaluates these paradigms, providing a comprehensive evaluation of commercial free tiers, an analysis of local-first alternatives, and a system architecture blueprint for constructing real-time agentic pipelines.

## **Commercial Meeting Transcription Applications: A Comparative Taxonomy**

Commercial meeting assistants utilize distinct capture modalities, varying from visible virtual bots to browser extension screen-scraping and operating-system-level audio loopback.1 The choice of capture architecture directly dictates the platform compatibility, user privacy posture, and accuracy of the resulting transcript.

### **Fathom**

Fathom represents a highly volume-generous free option for individual users, providing unlimited meeting recordings and raw transcripts with indefinite cloud storage.1 To capture meetings, Fathom traditionally deploys a visible recording bot to Zoom, Google Meet, or Microsoft Teams, though macOS users can leverage a native, bot-free desktop capture experience.1 The structural chokepoint of Fathom's free tier is its restriction on artificial intelligence capabilities: users are capped at five advanced summaries per month, reverting to basic, unformatted templates once the limit is exhausted.1 The platform is limited to desktop use on macOS and Windows, lacking a native mobile application.7

### **Otter.ai**

Otter focuses heavily on live, collaborative transcription and mobile synchronicity.1 It operates via a visible participant bot or direct audio input, transcribing speech in real-time while allowing multi-user highlighting and commenting.1 However, its free tier is highly restrictive, imposing a strict 300-minute monthly cumulative cap and a hard 30-minute limit per individual meeting, rendering it ineffective for standard corporate workshops or prolonged interviews.1 It lacks advanced summarization capabilities and integrations on the free plan.2

### **Fireflies.ai**

Fireflies is architected primarily for searchable archiving and multi-language support, covering over 100 languages.1 Unlike monthly rolling allowances, Fireflies implements a cumulative free storage ceiling of 800 minutes.1 Once this threshold is breached, older meetings are compressed or systematically deleted.1 While a free toggle allows unlimited raw transcriptions, advanced features (such as smart summaries and conversational help via the AskFred assistant) are restricted by a tight 20-credit monthly allowance.1

### **tl;dv**

Tailored for asynchronous, distributed teams, tl;dv stands out for its video-slicing and reel-creation capabilities.10 It allows free users to compile unlimited recordings and transcripts, but systematically purges this data after three months.2 Furthermore, tl;dv enforces a highly restrictive lifetime cap of only ten summaries, making its free tier a functional trial for intelligence-driven workflows, though highly effective for basic transcription and video clipping.2

### **Tactiq**

Tactiq bypasses the visible-bot paradigm entirely by operating as a lightweight Google Chrome browser extension.6 It intercepts live caption text directly from the browser window's Document Object Model (DOM) during Google Meet, Zoom, or Microsoft Teams sessions.9 Consequently, Tactiq captures meetings invisibly without storing audio or video files.8 This text-only architecture is secure, but forces a strict dependence on the host platform's native captioning accuracy.8 The free tier is capped at ten transcripts and five summary credits per month.6

### **Granola**

Granola is a macOS-exclusive desktop application that records meetings without sending a visible bot into the call, capturing audio directly from the device's audio output.1 Its free tier is structured as a trial, capping the user at 25 total transcripts and restricting access to integrations and conversational meeting history.1

### **Jamie**

Jamie operates as a native desktop application that captures audio directly from the operating system without deploying meeting bots.12 The free plan is highly limited, restricting the number of meetings processed, and requiring a local desktop environment, which prevents its use on mobile devices.13

### **Fellow**

Fellow treats meeting transcription as a structured workflow and task-management problem.20 Its enterprise-grade features are heavily gated, and the free tier allows only 5 total recordings, rendering it more of an evaluation sandbox than a sustained free solution.10

### **MeetGeek**

MeetGeek provides a basic plan with 3 hours of transcription per month, 3 months of transcript storage, and 1 month of audio storage.21 It supports automated transcription with unlimited basic summaries, automatic language detection, and is accessible via both a mobile app and a Chrome extension, utilizing an auto-join bot for meeting capture.21

### **Notta**

Highly optimized for multilingual teams, Notta supports 58 languages with high speech-to-text accuracy.15 Its free tier, however, is severely limited: it provides 120 minutes of monthly transcription but truncates individual sessions at a maximum of five minutes, restricting its utility to short voice memos or rapid updates.15

### **TicNote Cloud**

TicNote Cloud emphasizes turning meeting audio into structured, reusable knowledge and deliverables.14 The free plan includes 300 monthly credits and supports real-time transcription, speaker identification, and multi-level summaries.14 It distinguishes itself by supporting real-time capture, mind-map visualization, and cross-file querying, as well as connecting with specialized hardware for in-person capture.14

## **Comparative Matrix of Free Tier Meeting Transcription Platforms**

| Platform | Capture Modality | Free Transcribing Quota & Limits | Retention & Storage Policy | Language Support | Core Strengths & Key Features | Core Chokepoints & Limitations |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Fathom** 1 | Hybrid (bot-free on macOS; visible bot on Teams/Meet/Windows) 7 | Unlimited meetings and transcriptions 2 | Unlimited cloud storage with no deletion 2 | \~30 languages supported 1 | Unlimited recording volume; clean and structured meeting highlights 2 | Advanced summaries capped at 5 per month; lacks mobile application 1 |
| **Otter.ai** 1 | Visible participant bot or direct audio input 1 | 300 minutes per month 1 | Standard rolling storage 14 | Core focus on English, Spanish, French, Japanese 1 | Live, real-time collaborative text editing and commenting 1 | Hard 30-minute cap per meeting; no summaries or integrations 1 |
| **Fireflies.ai** 1 | Visible participant bot 1 | Unlimited raw transcription (with toggle enabled) 1 | 800 minutes of cumulative cloud storage 1 | Over 100 languages supported 1 | Robust global search across all historical transcripts 15 | Storage limit requires regular pruning; summaries are heavily gated 1 |
| **tl;dv** 6 | Visible participant bot 10 | Unlimited recordings and transcripts 2 | Hard 3-month data deletion policy 2 | 30+ languages supported 6 | Video clip extraction and shareable highlight reels 10 | Strict lifetime cap of only 10 summaries; no mobile app 2 |
| **Tactiq** 6 | Chrome extension (DOM caption scraping) 9 | 10 transcripts per month 6 | Cloud-saved transcripts 8 | 30+ to 60+ languages supported 15 | Entirely invisible; no bot joins; high privacy posture 8 | Captures text only (no audio/video); requires Chrome on desktop 8 |
| **Granola** 1 | Desktop system audio capture 1 | 25 transcripts total (trial basis) 1 | Local-first device storage 9 | 10 languages (desktop), 17 (iOS) 1 | Completely bot-free; offline support; system audio capture 9 | MacOS exclusive; lacks integration and history on free plan 1 |
| **Jamie** 6 | Desktop system audio capture 12 | Limited meetings 15 | Local-first device storage 6 | Strong European localized support 20 | Bot-free; privacy-oriented; runs outside browser 14 | Requires heavy desktop app; highly restricted meeting count 15 |
| **Fellow** 10 | Hybrid bot or native desktop capture 20 | 5 recordings total on free tier 10 | High enterprise governance 20 | 92 to 99+ languages 20 | Direct CRM integration; highly secure compliance pipelines 20 | Free tier functions merely as a temporary evaluation sandbox 10 |
| **MeetGeek** 21 | Auto-join bot, tab recorder, or mobile app 22 | 3 hours of transcription per month 21 | 3 months text retention; 1 month audio 21 | 60+ languages supported 22 | Mobile app access; unlimited basic summaries; file uploads 21 | Low monthly hourly limit; short cloud storage retention window 21 |
| **Notta** 15 | Visible bot or microphone audio input 15 | 120 minutes per month 15 | Standard cloud-saved transcripts 15 | 58 languages supported 15 | Exceptionally high transcription accuracy (98.86%) 15 | Strict 5-minute cap per individual transcription session 15 |
| **TicNote Cloud** 14 | Native client, hardware bundle, or web bot 14 | 300 monthly credits 14 | Integrated searchable knowledge base 14 | 17+ (real-time) to 70+ (post-call) languages 18 | Mind-maps; cross-file querying; shadow assistant 14 | Complex interface; hardware integration optimized 14 |

## **The Local-First and Self-Hosted Open-Source Paradigm**

Deploying meeting transcription solutions within local environments is increasingly favored by organizations prioritizing data sovereignty.4 This shift is accelerated by the operational economics of speech technologies.25

### **Operational Cost Modeling of Real-Time Pipelines**

Cloud-hosted voice platforms run highly intensive server-side pipelines.25 A typical voice session requires continuous streaming audio transport, neural voice activity detection, speech-to-text processing, large language model analysis, and high-quality text-to-speech generation.25 These compute requirements accumulate substantial platform costs:

* Speech-to-Text (STT) services cost approximately ![][image1] to ![][image2] per minute.25  
* Large Language Model (LLM) tokens average ![][image3] to ![][image4] per active conversation.25  
* Text-to-Speech (TTS) voice generation costs around ![][image3] to ![][image5] per minute.25  
* Media streaming and infrastructure overhead add roughly ![][image3] to ![][image4] per minute.25

These cumulative per-minute infrastructure expenses explain why commercial platforms impose strict time, volume, and storage ceilings on their free plans.1 By transitioning to local execution, enterprises leverage internal hardware resources (such as Apple Silicon Unified Memory or dedicated GPU clusters), completely bypassing recurrent API costs and the risk of vendor lock-in.4

### **Architectural Profiles of Local-First Solutions**

* **Meetily**: Meetily is a self-hosted, local-first meeting assistant built with a Rust-based backend and a TypeScript/Next.js frontend wrapped in Tauri.4 It runs completely on-device, capturing system-level audio directly from macOS, Windows, or Linux.4 Meetily utilizes highly optimized local models, such as Parakeet or Whisper, for local speech-to-text processing, and integrates with Ollama for local LLM summarization.4 To address speaker attribution, Meetily's development roadmap focuses on dual Voice Activity Detection (VAD) to process microphone input and system output as separate channels, labeling segments as "Me" (local microphone) or "Them" (system audio) in real-time.30  
* **ownscribe**: This macOS native command-line tool utilizes PyAnnote and WhisperX (powered by faster-whisper and CTranslate2) to achieve on-device transcription and speaker diarization.5 Rather than virtual audio drivers, ownscribe leverages macOS Core Audio Taps (introduced in macOS 14.2) to capture system audio directly from the speaker output, optionally mixing in local microphone input.5 After transcription, ownscribe forwards the text stream to a local Phi-4-mini model (\~2.4 GB, running on llama.cpp) or a local Ollama endpoint, generating structured notes, action items, and decisions through configurable templates.5  
* **agent-cli**: Implemented as a lightweight Python daemon, agent-cli continuously monitors the system microphone.31 It uses local Voice Activity Detection to segment incoming audio streams dynamically.31 Once silence is detected, the audio chunk is transcribed via an ASR provider (such as Wyoming, OpenAI, or Gemini) and logged to a JSONL file with precise timestamps.31 The resulting text segment can then be processed in real-time by a local Ollama instance (defaulting to Gemma-3:4b) to add punctuation, remove filler words, and format the output.31

## **Real-Time Open-Source Speech-to-Text Engines**

Establishing a real-time, low-latency pipeline requires transitioning from standard batch audio transcription to streaming speech-to-text engines.27 Three primary open-source engines form the foundation of modern live transcription architectures.

### **Whisper.cpp**

Whisper.cpp is a highly optimized C/C++ port of OpenAI's Whisper model designed for minimal memory consumption and rapid inference.28 It supports hardware acceleration across mixed GPU setups using Vulkan, alongside native Apple Silicon Metal and NVIDIA CUDA architectures.28 For local execution, Whisper.cpp balances latency and accuracy, running models like Whisper medium or the highly optimized large-v3-turbo with low VRAM footprint.28 Whisper.cpp is ideal for resource-constrained systems, such as edge devices or local developer workstations.28

### **Faster-Whisper**

Faster-Whisper replaces the vanilla PyTorch implementation of Whisper with CTranslate2, a highly optimized engine that implements weight quantization and speed optimizations.5 Faster-Whisper achieves up to four times the transcription speed of the original Whisper implementation while dramatically reducing VRAM usage, making it the preferred backend for modern Python-based open-source projects.4

### **WhisperLive**

WhisperLive provides a production-grade, real-time, streaming implementation of Whisper.32 Running as a local or Dockerized server, WhisperLive establishes persistent WebSocket connections with client devices, accepting raw PCM audio streams and returning real-time transcription segments with word-level timestamps, custom vocabulary support, and active speaker diarization.32 It supports Faster-Whisper, NVIDIA TensorRT-LLM, and Intel OpenVINO backends, enabling GPU-accelerated, ultra-low-latency execution.32

## **Engineering Real-Time Agentic Pipelines**

A real-time agentic pipeline ingests a streaming audio source, transcribes it in real-time, routes the text stream to a contextual decision-making layer, executes LLM-driven actions (such as generating notes, checking for logical fallacies, or querying related documents), and optionally speaks back to the user.3 Open-source frameworks like Pipecat and LiveKit Agents simplify this orchestration.3

### **Pipecat's Frame-Based Pipeline Architecture**

Pipecat is a modular, event-driven, open-source Python framework created by Daily.3 It processes streaming multimodal data (audio, text, images, and video) as discrete *Frames* flowing through a directed pipeline of *Frame Processors*.3

               \[ User Audio Input \]  
                        │  
                        ▼  
               ┌────────────────┐  
               │  Transport.in  │  
               └────────┬───────┘  
                        │ (Audio Frames)  
                        ▼  
               ┌────────────────┐  
               │  VADProcessor  │ (Silero VAD)  
               └────────┬───────┘  
                        │ (VAD-chunked Audio)  
                        ▼  
               ┌────────────────┐  
               │   STTService   │ (Whisper / Deepgram)  
               └────────┬───────┘  
                        │ (Transcription Frames)  
                        ▼  
               ┌────────────────┐  
               │   LiveAgent    │ (Custom FrameProcessor)  
               └────────┬───────┘  
                        │  
                        ▼  
              

In a standard Pipecat speech-to-text pipeline, raw audio is ingested by a transport layer (such as WebSockets, Daily WebRTC, or Local Audio Taps) and pushed downstream to a Voice Activity Detection (VAD) processor, typically utilizing Silero VAD.36 The segmented audio is then transcribed by an STT service (such as WhisperSTTService or SpeechmaticsSTTService).42  
To pipeline the transcription stream in real-time to an analytical agent without interrupting the core conversational loop, developers implement a custom FrameProcessor to intercept the text frames.42 The following code snippet demonstrates how to construct a non-blocking transcription logger in Pipecat that intercepts TranscriptionFrame objects to run real-time logging, leaving the primary pipeline to process downstream functions:

Python  
import asyncio  
from pipecat.frames.frames import Frame, InterimTranscriptionFrame, TranscriptionFrame  
from pipecat.processors.frame\_processor import FrameDirection, FrameProcessor

class RealTimeAgentPipeline(FrameProcessor):  
    """  
    Custom Pipecat Frame Processor that intercepts completed transcription   
    frames and pipelines them asynchronously to a background analysis agent   
    without blocking the real-time audio pipeline.  
    """  
    def \_\_init\_\_(self, agent\_client):  
        super().\_\_init\_\_()  
        self.agent \= agent\_client

    async def process\_frame(self, frame: Frame, direction: FrameDirection):  
        \# Always call the parent process\_frame to maintain frame lifecycle  
        await super().process\_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):  
            \# Non-blocking fire-and-forget execution to prevent pipeline lag  
            asyncio.create\_task(self.\_route\_to\_agent(frame.text, frame.timestamp))  
        elif isinstance(frame, InterimTranscriptionFrame):  
            \# Optional: handle partial real-time streaming tokens for keyword spotting  
            pass

        \# Forward the frame downstream to maintain conversational continuity  
        await self.push\_frame(frame, direction)

    async def \_route\_to\_agent(self, text: str, timestamp: float):  
        try:  
            \# Asynchronously send the transcript segment to the downstream analytical agent  
            await self.agent.analyze\_segment\_async(text, timestamp)  
        except Exception as e:  
            \# Log errors from external RAG/API systems without crashing the media stream  
            print(f"Agent pipeline routing failed: {e}")

Furthermore, Pipecat manages conversation context through structured aggregators (LLMContextAggregatorPair).46 When a user or assistant finishes speaking, events such as on\_user\_turn\_stopped and on\_assistant\_turn\_stopped emit a complete turn transcript.46 These structured turn events are ideal for sending compiled segment payloads to external APIs or microservices via asynchronous HTTP libraries, ensuring real-time note-taking and documentation proceed concurrently.46

### **LiveKit's WebRTC Room-Based Orchestration Model**

LiveKit Agents operates on a WebRTC-native room model, treating AI agents as stateful, programmable server-side participants that join virtual rooms alongside human users.3  
For multi-user scenarios where multiple speakers must be transcribed simultaneously on separate channels, LiveKit Agents provides native multi-participant tracking.38 In this architecture, a supervisor agent server monitors the WebRTC room.38 When a participant connects, the supervisor intercepts the event and spawns an isolated AgentSession specifically bound to that participant's identity.48 This session is configured with a Voice Activity Detector and a dedicated speech-to-text plugin (e.g., Deepgram Nova-3), transcribing the participant's audio stream in real-time without mixing it with other room members.48 The transcript is then published back to the room using LiveKit's unified lk.transcription text stream topic, allowing client applications or downstream agent instances to intercept the data in real-time.47

### **Real-Time Retrospective and RAG Integration Pipelines**

To perform real-time retrieval-augmented generation (RAG) or call external tools (such as checking document repositories, searching the web, or pulling contextual notes) during a meeting, the agent uses semantic search or tool-calling hooks.37

┌────────────────────────────────────────────────────────┐  
│                      LiveKit Room                      │  
│                                                        │  
│  ┌─────────────────┐             ┌──────────────────┐  │  
│  │ Human Speaker 1 ├─(Audio)────►│ STT Agent        │  │  
│  └─────────────────┘             └────────┬─────────┘  │  
│                                           │            │  
│                                     (Live Text)        │  
│                                           ▼            │  
│  ┌─────────────────┐             ┌──────────────────┐  │  
│  │ Downstream Client│◄(Transcripts│ AgentSession     │  │  
│  │ UI & Captions   │  lk.trans)──┤ (Context Logic)  │  │  
│  └─────────────────┘             └────────┬─────────┘  │  
└───────────────────────────────────────────┼────────────┘  
                                            │  
                                            ▼  
                               ┌────────────────────────┐  
                               │     Retrieval Layer    │  
                               │  (LlamaIndex / Qdrant) │  
                               └────────────┬───────────┘  
                                            │  
                                    (Context Payload)  
                                            ▼  
                               ┌────────────────────────┐  
                               │    Downstream LLM      │  
                               │ (Gemini/GPT Reasoning) │  
                               └────────────────────────┘

When designing an open-source real-time RAG voice agent (e.g., using LiveKit Agents, Qdrant as the vector database, and LlamaIndex as the data framework), developers configure the agent's core routing logic to intercept transcription segments.37 The agent checks the transcribed text for semantic intent or specific entity triggers.27  
If a query requires contextual documentation, the text is vectorized and matched against Qdrant's vector collection.37 The retrieved document chunks are then appended to the LLM's system prompt dynamically.37 To prevent retrieval latencies from blocking the audio stream, the vector search is offloaded to a separate, asynchronous task thread, and the resulting context is cached to prevent redundant, expensive lookups.37

## **Architectural Trade-offs and Systemic Recommendations**

When choosing between commercial platforms and open-source real-time agentic pipelines, systems architects must evaluate key latency, hardware, and operational trade-offs.

### **Latency Modeling and Turn Detection**

For real-time speech processing, sequential "cascaded" pipelines (waiting for a speaker to complete an entire sentence, transcribing it, sending it to the LLM, and synthesizing the response) introduce significant, unnatural latencies.27 Production-grade voice agents require streaming pipelines where STT streams partial results as the user speaks, the LLM streams tokens, and the TTS engine begins synthesizing speech on the first few tokens.25  
The cumulative real-time latency of an AI agent pipeline can be mathematically modeled as:  
![][image6]  
Where:

* ![][image7] is the voice activity detection threshold (typically ![][image8] to ![][image9]).43  
* ![][image10] is the speech-to-text processing time (typically ![][image8] to ![][image9]).25  
* ![][image11] is the LLM's Time-to-First-Token under streaming conditions (typically ![][image12] to ![][image13]).25  
* ![][image14] represents the execution latency of tool calling, vector database retrieval, or document searches (![][image15] to ![][image16]).37  
* ![][image17] is the text-to-speech Time-to-First-Chunk latency (typically ![][image8] to ![][image9]).25  
* ![][image18] is the media transport routing delay using WebRTC (typically ![][image19] to ![][image20]).25

Under optimal network conditions, a standard streaming pipeline achieves an end-to-end latency of ![][image13] to ![][image21], providing a natural conversation flow.3 However, incorporating extensive, un-optimized RAG queries or heavy on-device embeddings can push latency values beyond ![][image22], causing conversational overlap and sluggish turn-taking.37  
Furthermore, standard VAD-based turn detection often struggles with mid-sentence pauses, triggering premature interruptions when a user stops to think.27 Modern open-source implementations solve this by deploying semantic turn-detection classifiers (such as LiveKit's custom transformer models) to analyze the actual linguistic meaning of the partial transcript, determining if the utterance is structurally complete before signaling the LLM to respond.27

### **Hardware and VRAM Management**

Deploying local-first, on-device transcription models requires substantial memory resources.28 A local instance of ownscribe or Meetily executing Whisper large-v3 or large-v3-turbo for high-accuracy speech-to-text requires approximately ![][image23] to ![][image24] of VRAM, with additional VRAM requirements for local LLM inference engines like Ollama.5  
For resource-constrained infrastructure or shared developer workstations, architects should utilize INT8-quantized representations of the Whisper model via Faster-Whisper, or employ high-performance C++ runtimes such as Whisper.cpp.5 Alternatively, deploying a local WhisperLive server on a dedicated central workstation with NVIDIA GPU acceleration provides an enterprise-wide real-time transcription endpoint, offloading compute requirements from end-user laptops.32

### **Strategic Architectural Recommendations**

* **For Individual Evaluation and Instant Setup**: Individuals and small teams should deploy **Fathom**.1 Its unlimited free recordings, raw transcriptions, and clean, structured summaries provide the most cost-effective and friction-free starting point, provided users do not require immediate native mobile apps or cross-meeting multi-call analysis.1  
* **For Absolute Data Sovereignty and Local Environments**: Compliance-centric, legal, and healthtech organizations should deploy **Meetily** or **ownscribe**.4 Operating 100% locally on-device, these tools eliminate cloud API costs, guarantee complete data sovereignty, and run indefinitely without subscription fees.4  
* **For Building Custom real-time Agentic Applications**: Systems architects and developers building voice-enabled applications, live lecture translation services, or interactive agentic meeting bots should utilize **Pipecat** or **LiveKit Agents**.3 Pipecat should be selected when building highly customized voice-first pipelines requiring precise control over frame processing, modular service swapping, and linear Python structures.3 LiveKit Agents is the optimal choice when the system requires production-grade WebRTC media routing, multi-participant room architectures, native telephony integration, and a battle-tested agent server orchestration layer.3

#### **Works cited**

1. Meeting note tool pricing: Granola vs. Fireflies vs. Fathom vs. Otter, accessed June 14, 2026, [https://www.granola.ai/blog/meeting-note-tool-pricing-granola-vs-fireflies-fathom-otter](https://www.granola.ai/blog/meeting-note-tool-pricing-granola-vs-fireflies-fathom-otter)  
2. Free Account Features Comparison 2026 \- AI Meeting Tools Complete Guide, accessed June 14, 2026, [https://summarizemeeting.com/en/comparison/free-account-features](https://summarizemeeting.com/en/comparison/free-account-features)  
3. Vapi vs Pipecat vs LiveKit: Voice Agent Frameworks Compared (2026) \- Inworld AI, accessed June 14, 2026, [https://inworld.ai/resources/vapi-vs-pipecat-vs-livekit](https://inworld.ai/resources/vapi-vs-pipecat-vs-livekit)  
4. GitHub \- Zackriya-Solutions/meetily: Privacy first, AI meeting assistant with 4x faster Parakeet/Whisper live transcription, speaker diarization, and Ollama summarization built on Rust. 100% local processing. no cloud required. Meetily (Meetly Ai \- https://meetily.ai) is the \#1 Self-hosted, Open-source Ai meeting note taker for macOS & Windows., accessed June 14, 2026, [https://github.com/Zackriya-Solutions/meetily](https://github.com/Zackriya-Solutions/meetily)  
5. GitHub \- paberr/ownscribe: Local-first meeting transcription and summarization CLI, accessed June 14, 2026, [https://github.com/paberr/ownscribe](https://github.com/paberr/ownscribe)  
6. AI Note Taker Apps I Tested in Real Meetings: My 5 Best Free Picks (2026), accessed June 14, 2026, [https://tldv.io/blog/free-ai-note-taking/](https://tldv.io/blog/free-ai-note-taking/)  
7. What devices is Fathom compatible with?, accessed June 14, 2026, [https://help.fathom.video/en/articles/296576](https://help.fathom.video/en/articles/296576)  
8. Tactiq \- Functies, prijzen & ervaringen (2026) \- ToolGuide, accessed June 14, 2026, [https://toolguide.io/en/tool/tactiq/](https://toolguide.io/en/tool/tactiq/)  
9. Granola vs Tactiq: AI Meeting Notes Comparison 2026 \- Zachary Proser, accessed June 14, 2026, [https://zackproser.com/blog/granola-vs-tactiq](https://zackproser.com/blog/granola-vs-tactiq)  
10. Tactiq Alternatives for AI Meeting Notes in 2026, accessed June 14, 2026, [https://meetingnotes.com/blog/tactiq-alternatives](https://meetingnotes.com/blog/tactiq-alternatives)  
11. Fathom vs tl;dv: Which AI Meeting Assistant Is Worth It? (2026) \- alfred\_, accessed June 14, 2026, [https://get-alfred.ai/compare/fathom-vs-tldv](https://get-alfred.ai/compare/fathom-vs-tldv)  
12. Fathom Pricing: How Much Does Fathom Really Cost in 2026 \- Sonix, accessed June 14, 2026, [https://sonix.ai/resources/fathom-pricing/](https://sonix.ai/resources/fathom-pricing/)  
13. Fathom AI Review: Free Meeting Assistant 2026 \- Pricing & Features, accessed June 14, 2026, [https://screenapp.io/blog/fathom-notetaker-review](https://screenapp.io/blog/fathom-notetaker-review)  
14. 7 AI Meeting Transcription Tools Comparison 2026 (Ranked): Best Apps for Transcription, Notes, Summaries, and Team Workflows \- TicNote Cloud, accessed June 14, 2026, [https://ticnote.com/en/blog/ai-meeting-transcription-tools-comparison](https://ticnote.com/en/blog/ai-meeting-transcription-tools-comparison)  
15. Best Free AI Meeting Tools 2026: Complete Comparison Guide, accessed June 14, 2026, [https://summarizemeeting.com/en/blog/free-ai-meeting-tools](https://summarizemeeting.com/en/blog/free-ai-meeting-tools)  
16. Fathom vs tl;dv: which meeting tool should you use in 2026? \- Fabric.so, accessed June 14, 2026, [https://fabric.so/comparison/fathom-vs-tl-dv](https://fabric.so/comparison/fathom-vs-tl-dv)  
17. ai-note-taking-app · GitHub Topics, accessed June 14, 2026, [https://github.com/topics/ai-note-taking-app](https://github.com/topics/ai-note-taking-app)  
18. Best Meeting Transcription Tools in 2026: TicNote Cloud vs Notta vs Otter.ai vs Tactiq \+ Alternatives Compared, accessed June 14, 2026, [https://ticnote.com/en/blog/best-meeting-transcription-tools-2026](https://ticnote.com/en/blog/best-meeting-transcription-tools-2026)  
19. Fathom vs Tl;dv: Which AI Meeting Assistant Is The Best? (2026) \- TheBusinessDive, accessed June 14, 2026, [https://thebusinessdive.com/fathom-vs-tldv](https://thebusinessdive.com/fathom-vs-tldv)  
20. The 10 Best AI Note Takers in 2026 (Tested and Ranked) \- Meeting Notes, accessed June 14, 2026, [https://meetingnotes.com/blog/best-ai-note-takers](https://meetingnotes.com/blog/best-ai-note-takers)  
21. Fathom AI Pricing 2026: Is It Still Worth It for Modern Teams? \- MeetGeek, accessed June 14, 2026, [https://meetgeek.ai/blog/fathom-ai-pricing](https://meetgeek.ai/blog/fathom-ai-pricing)  
22. Tactiq Pricing Review 2026: Plans, Limits, and The Best Alternative \- MeetGeek, accessed June 14, 2026, [https://meetgeek.ai/blog/tactiq-pricing](https://meetgeek.ai/blog/tactiq-pricing)  
23. Fellow vs Fathom AI: Which AI Note Taker Is Right for Your Team?, accessed June 14, 2026, [https://fellow.ai/blog/fellow-vs-fathom-ai/](https://fellow.ai/blog/fellow-vs-fathom-ai/)  
24. Meetgeek \- Record and transcribe your online calls \- AppSumo, accessed June 14, 2026, [https://appsumo.com/products/meetgeek/](https://appsumo.com/products/meetgeek/)  
25. Voice agents | LiveKit, accessed June 14, 2026, [https://livekit.com/voice-agents](https://livekit.com/voice-agents)  
26. Top Voice AI Agent Frameworks in 2026: A Complete Guide for Developers \- Medium, accessed June 14, 2026, [https://medium.com/@mahadise0011/top-voice-ai-agent-frameworks-in-2026-a-complete-guide-for-developers-4349d49dbd2b](https://medium.com/@mahadise0011/top-voice-ai-agent-frameworks-in-2026-a-complete-guide-for-developers-4349d49dbd2b)  
27. Voice Agent Architecture: STT, LLM, and TTS Pipelines Explained \- LiveKit, accessed June 14, 2026, [https://livekit.com/blog/voice-agent-architecture-stt-llm-tts-pipelines-explained](https://livekit.com/blog/voice-agent-architecture-stt-llm-tts-pipelines-explained)  
28. Best open source api for speech to text transcriptions and alternative for open AI \- Reddit, accessed June 14, 2026, [https://www.reddit.com/r/LocalLLaMA/comments/1rybql4/best\_open\_source\_api\_for\_speech\_to\_text/](https://www.reddit.com/r/LocalLLaMA/comments/1rybql4/best_open_source_api_for_speech_to_text/)  
29. Meetily (Meetly AI) \- Privacy-First AI Meeting Assistant | Otter.ai & Granola Alternative, accessed June 14, 2026, [https://meetily.ai/](https://meetily.ai/)  
30. Selective Input/Output Audio Capture \+ Muted-Mic Awareness · Issue \#337 · Zackriya-Solutions/meetily \- GitHub, accessed June 14, 2026, [https://github.com/Zackriya-Solutions/meeting-minutes/issues/337](https://github.com/Zackriya-Solutions/meeting-minutes/issues/337)  
31. agent-cli/docs/commands/transcribe-live.md at main \- GitHub, accessed June 14, 2026, [https://github.com/basnijholt/agent-cli/blob/main/docs/commands/transcribe-live.md](https://github.com/basnijholt/agent-cli/blob/main/docs/commands/transcribe-live.md)  
32. collabora/WhisperLive: A nearly-live implementation of OpenAI's Whisper. \- GitHub, accessed June 14, 2026, [https://github.com/collabora/WhisperLive](https://github.com/collabora/WhisperLive)  
33. How to make Whisper STT real-time transcription \[Part 1\] | by Progressing Llama \- Medium, accessed June 14, 2026, [https://medium.com/@pcb.it18/how-to-make-whisper-stt-live-transcription-part-1-79c628984fc6](https://medium.com/@pcb.it18/how-to-make-whisper-stt-live-transcription-part-1-79c628984fc6)  
34. live-transcription · GitHub Topics, accessed June 14, 2026, [https://github.com/topics/live-transcription](https://github.com/topics/live-transcription)  
35. transcription · GitHub Topics, accessed June 14, 2026, [https://github.com/topics/transcription?l=shell\&o=desc\&s=updated](https://github.com/topics/transcription?l=shell&o=desc&s=updated)  
36. Overview of Pipecat, accessed June 14, 2026, [https://docs.pipecat.ai/pipecat/learn/overview](https://docs.pipecat.ai/pipecat/learn/overview)  
37. Lessons from implementing RAG in a real-time voice agent (LiveKit) | by Jorge Jarne, accessed June 14, 2026, [https://medium.com/@jorge.jarne/lessons-from-implementing-rag-in-a-real-time-voice-agent-livekit-43f0689bf565](https://medium.com/@jorge.jarne/lessons-from-implementing-rag-in-a-real-time-voice-agent-livekit-43f0689bf565)  
38. Introduction | LiveKit Documentation, accessed June 14, 2026, [https://docs.livekit.io/agents/](https://docs.livekit.io/agents/)  
39. livekit/agents: A framework for building realtime voice AI agents 🎙️ \- GitHub, accessed June 14, 2026, [https://github.com/livekit/agents](https://github.com/livekit/agents)  
40. pipecat-ai/pipecat: Open Source framework for voice and multimodal conversational AI \- GitHub, accessed June 14, 2026, [https://github.com/pipecat-ai/pipecat](https://github.com/pipecat-ai/pipecat)  
41. RoomKit, Pipecat, TEN Framework, LiveKit Agents: Choosing the Right Conversational AI Framework, accessed June 14, 2026, [https://www.roomkit.live/blog/choosing-the-right-conversational-ai-framework/](https://www.roomkit.live/blog/choosing-the-right-conversational-ai-framework/)  
42. pipecat/examples/transcription/transcription-whisper.py at main ..., accessed June 14, 2026, [https://github.com/pipecat-ai/pipecat/blob/main/examples/transcription/transcription-whisper.py](https://github.com/pipecat-ai/pipecat/blob/main/examples/transcription/transcription-whisper.py)  
43. Speech to Text \- Pipecat, accessed June 14, 2026, [https://docs.pipecat.ai/pipecat/learn/speech-to-text](https://docs.pipecat.ai/pipecat/learn/speech-to-text)  
44. pipecat/examples/transcription/transcription-speechmatics.py at main \- GitHub, accessed June 14, 2026, [https://github.com/pipecat-ai/pipecat/blob/main/examples/transcription/transcription-speechmatics.py](https://github.com/pipecat-ai/pipecat/blob/main/examples/transcription/transcription-speechmatics.py)  
45. What's the recommended way to capture full call transcripts \+ per-turn latencies from a pipecat pipeline? · Issue \#3977 \- GitHub, accessed June 14, 2026, [https://github.com/pipecat-ai/pipecat/issues/3977](https://github.com/pipecat-ai/pipecat/issues/3977)  
46. Transcriptions \- Pipecat, accessed June 14, 2026, [https://docs.pipecat.ai/api-reference/server/utilities/turn-management/transcriptions](https://docs.pipecat.ai/api-reference/server/utilities/turn-management/transcriptions)  
47. Transcription text streams not generated for more than one participant · Issue \#3657 · livekit/agents \- GitHub, accessed June 14, 2026, [https://github.com/livekit/agents/issues/3657](https://github.com/livekit/agents/issues/3657)  
48. agents/examples/other/transcription/multi-user-transcriber ... \- GitHub, accessed June 14, 2026, [https://github.com/livekit/agents/blob/main/examples/other/transcription/multi-user-transcriber.py](https://github.com/livekit/agents/blob/main/examples/other/transcription/multi-user-transcriber.py)  
49. Text and transcriptions \- LiveKit Documentation, accessed June 14, 2026, [https://docs.livekit.io/agents/multimodality/text/](https://docs.livekit.io/agents/multimodality/text/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADkAAAAZCAYAAACLtIazAAACeElEQVR4Xu2XT4hPURTHD0OhSeRPNMOUIslC2cnKSiymLGaSjdgoNYkixUpKkWShRFYSSWY3RdlMsxklJEo2ImMhC/InhPN1z/nNed/fvfN7tr/ep769e77n3vPefe/dd38/kYbuZTcb3cYO1R/VMCe6gdmSJnfejqftuCx2Mk6qPqm+qvZTrhO3JdV9rlpAOWefakr1S3WGcjkGJNXsCAputnYcwINxcfdD/Ew1EeIScyXVWm1xj8UrWz0SuAnvQnxd9THEOVCHrzNLbmIfyF9IsQNvEZvEuOoteeekvR7iORlvO3nOPdUXaa+TBZ36QhvclfSEncchF4F3lU0CfS6Rt8V85wLFDrxXbCr9qlFpfxhF0Ak6YMcc3ocp+Y6/mifIHzB/l8U/LGZK9d2rPckVMl0M+qZaW+kx88lyvrNJUv4w+fiowT9mcalOzr+jWmXt2pMEuONPpDpZrEMndzJQ8p1tkvIj5C82/4rFpTrsL1E9CPF/TdLBgPhko58rVvKddZLyh8hfav4pi0t12Oc+tSf5WrXX2j5gY2i7nytW8p1ZkvLHycfrBn+PxfjI5erE+pdV60MO1J4kOr0J7eg7nyl24L1gk0Cf0tfV90rsv6X6v609Jmk7ivKbgPaMX/mfoe0nWhPaYIhiB57/kADzVAdDDHCRT8k7KtV6vkQYeEfYDPgkO4I96oa1McB/oWA9ReBhm3HOmhfxk24I3lbzIogvkoebcTPEO6V9HFN7kgD/Pnxd4Mkur6b/MV9SflLSl/i7pDUXGVQ9JA/4k7slaU+8Vk23QO6lTL+KvdV0i0eq95KWGYR27rxZat+VhoaGhoaGLucvjP/bvnf7trsAAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAZCAYAAAChBHccAAACPUlEQVR4Xu2WP0hXURTHT0lRQlaQkkgpUQ3RELSIODkGITQo4RI0KAUVDYmQIFiTEqLQUjgG0RC0OAgt0aIgFVJz6CDolJBS/ul8f+ccPe+8d/s5KrwPHN49n3N+93d97/3ulahk/3A7ioPCDY5tju5Y2M8cJln0C70+12u9b1IGOX5x/Oa4G2rVeEcy73eO2lAzJkh6NjlGQq2QDY7rOsYHDT8G+NJpl89zfHZ5iiMkc53XvEbzxp0OYY2jxeXoiWvIUbTgleDrQm7AnYoy8IljMbhRys53VPNV596r63UuBxqa3Bjgg3gixhdX88C9jjKAnpfBtan3IJ9x+ZS6m87lQAOiT69FWE8k5Q17RZ4G36z+VvCeanNXOEu7jQi8e5cyHemJUt64RlJ/HDw2A/j+4I0PJPWTsVAE7tBXyv4ReM+N1CJT3uggqT8I/rT6V8G3kuw4PzjmSH4LewYT+ifhfdEiU964TFJ/FPwZ9cPBez6S9KA3yU+OOzq2hVx1Y/NFi0x54xBJfSD4c+p7gvdg+642f6W44MbeG9jCiiaBwyP+H+hJ7Ta219/T/MROh1B18X/d2BovuDHoCrkBZwccOMZx3+Vgi+NbcE8of6MQQ85ddD7JGMcbHaPRTkS8rx44bKcGju84sX3ZFefa1XmQj7v8IceSywFOcPQ1B58D/03iUEIznkRDtlzhOEkdBwl2pnWSd9rTyTEbHLA7/ZbjD8dktlzhGUnPsl7xxPDb2DPxDpWUlJSUHFz+AahYsMozx6tNAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAZCAYAAAChBHccAAAB/klEQVR4Xu2WMUhXURSHT0mUDpKQoogKQQ7hELhJk2OL4JBEi+AiCCINRWBTNCUhDi1JoyAOgatjudSSITWHCgpOCioq1fl5z8nz//ku+jaF98Hh3fude6/H9y73/kUqLg9PWFwVHmn81RjixGXmuqSi39nzjT2b4yDjlcaOxp7GCOXOY0HSuj81GijHbLHIcazRa20s7sQ2wB9dCv1VjeXQz3FD0lqd1q+zftv/EYnv5j0uRFHB2+Qbqe/A3WZJfNZYJzclxeuBRcnnzoCB7aENPkn6Io6/FQZuliWBMe/J9ZkvonTxiFF7FuFjmJx3fItMku8yP0gelCq+VU6LQOxr3KsZkS8y550HkvLPyOMwgH9BHpQqHuANrUjtP4F97uSKzHmnX1J+nHyT+Q/kQeniHUyKXyL6ogVz3umWlJ8gf8f8a/KgVPG/NYat7ZN6Qtt90YI571yTlH9JvsP8U/KgVPEYuBba0Tu71HfgfrEkMCZ32vBZD0oVfxTaPuluaIPH1Hfg/IIDtzTGQh/80fhB7rkUrwdKFT+tMWdtTPIbEfs1Aofj1HlrLoI+4n5wD81F0J8h53yRlL/JiRz4NYlLCZPwJVpq0yfUS8p/lXQyHUja05EBjW/kgL/peY1DjY+16RNwRG9Kuo2xjTck3fQX/g3Fb6iioqKi4uryD0xFpDofjW6bAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAZCAYAAAChBHccAAAB5klEQVR4Xu2WyytFURTGl2eUZELKTDGQmX9CDMzITEwUM2VmqJSSP8BQ8shrbCgTJpQomchzIAMKIazP3vvedZa9zr3De+v86uus9a3Vuvvcc+7elyijdBjWRrnQx/phDelCKVNJbtEL/jrrr82yyTPDema9ssZUrRjwBa1pUzDKumd9seZULQoae3yMRQdkDM5YeyI/ZR2I3GKa9UJuHrSeLOfYYN2JfJn1JPIosQU/Kr9R5QF4TdpMIW3xqFVHvF7lJUBDm4jBNrknEjgWNQm8JW2mYC1+kez5l9qUoAEa99cYoUdj+RbW4j8oPqfg/FbKN0FvrI5Ehz3E8i2sxVtzLD9BFeuEkjeB9zxgDbF8C/Tih6mx5lh+FDTKJyH92BDLt0DvpjbJnmP5Oa5YIz4Ojd0iDn5siOVboHdLm+Q2h9icgvNRvBax9ANhn9bAO9dmCujf0Sa588Oa/61NyaeIw4B2EYNBlQfghQMO1LEmRK5B/642Kf+qauBNaVOCPXbFx2iu8dfOXEe+hu00MO89CXKoS/mgllzNOpXxDa+KvJ/+z4+Cf5PhvcOTaEmW/6gnVz8ktzO9syoSHUQDrCPlTZI7sW/JvZ43rAdyW7IG+/0Fa5/cZzUky+kUdacZGRkZGWXBLw0fqbSISLhKAAAAAElFTkSuQmCC>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAZCAYAAAChBHccAAACOklEQVR4Xu2WT0gVURTGj0qQgVKQmoQ+EGohLQJzE24SV22EFoq4CdoEgkSLJDAQolUR0cJF/lm0EKKFuzbiKtroRkV0aWItBFcKKvbHzvfuOc8z581977V7wvzgY+75zpk7d+beuTNEGdXDkDfOC/dZp6xBn6hmaikM+q0cX8mxyRYJL1j7rEPWI5crx2cK/W6wLrkcOGE9YbWw6ll9rO+2II3frC5po3PFtgEuumDiddY3E8e4QKGvdonrJG4tVATged1LVKSQNuA95ze6WIF32ZuOr6wfzntDxf0hnmBN038sXZx03bTBPIUZUVZMzgIPFysFaiadd1d8i48rQqfosRzT0BpPzFd0iYw7Pyf+A+OV6ifKNTobBHTEupGoiA8y5iu3KeSfOh+bAfwx4yHGO/WT9UVivLxlwRNapeRNYJ0rsUHGfKWXQn7U+VfEnzIe4pyJn4lXMSi2M2H9tI5ivnKTQh5boOWq+C+d70HNojct26yH0taB3DJt9dMGGfOVGgr5585vE3/YeNhSPeX6zyd3TNv6yoGLFXib3nSgJrbb6F4/I3F3oSIA75fzEtikDrDDtMGAixV4+oEDF1kjJgZ/WWvO8+v5I+sPhZlSGijUfDBeEe9Yc9JGsX4RsV4t8LCdKq/FsyCGOo3XI54F8XsT4xcFu5xli4rPSwV/k/gooRgz0ZxM58H/BvJLFHamY0o+KdDPWnYe0Cf9icI/zGwynecOhZpdOepSrpiK7jQjIyMj41zwDzrCraTVcFN3AAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,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>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAaCAYAAADIUm6MAAABpElEQVR4Xu2WvytGYRTHD8pGsjD4mRSlTEazYiCDjMwGJjblD2CQlKzKIousBguKvDYZLVJ+KwrhfJ3n1nlP5/LK5b3lfupT9/mee9/n9L7n3vsSZWT8DzbYt2+YGtDMkJPZJtucrGhUk3zjmlKSBnMmB6c2KBabbInJJkga7zd5OTtnsqIxbgPmmvyRqGJrbJgmvPlOPWUkTe/bwg8YtsFvMEXSeJ8tMIsktUd2WuWrId9WWUQz+b/eALtGUlti59ld9oVtVOcVzD35G0XMkF8/sUHggOT8BlsIeJ+FrNaGX1HIfKNeodadbJNaa3bYG3bPFgLeXmPsqw0/A4+7QuYbo7Kl1mfqWNPK1rO95DcIvLyS/DyWZZILRkxusY2sqGPNkTrG+S1qHeE1iPcKcvt+yWOQfSB5dl8GMedP5H9oBGpd7CjJm9bjll0I4vzD/PIH3h7d5OeJgG/zguJnsZ2tU+se8pvxsnX23IZJgbsem+JG8ji2Acn5+KNmM02HkyVO3AYYEYwcbuIIjONV8JmdJbke4lfDaN6xk9EFGRkZGX/HO//ic9uYERkSAAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD0AAAAZCAYAAACCXybJAAACQUlEQVR4Xu2WTYiOURTH/zSJjWaBlI3EZlYkGxLJUhYyVspiNj4iwpKtBYpiQSY7FizsphlWSmHho8zYqElIPprJZ0g4/845nDnvfd5ebF66v/r33vM/53nuuc97nw+gUqn87xwQ7chm4JDoreijaCDlnMWiW6Lvomsp1zVcFH2BNkntnJr+yZjoaogfiG6EmKyBnsNZmuKupGnRs1Funl5vivNO4QW9mbyuomnR99C86HM2nmcxfyMj5nctTYv2rZ+J/uEwjpxH2XdWi/aLzkB3zXTo8+IEdIc57OuCaG3wnEWiIdGoaDt+c2f9zaKvhHHkNMq+s1V0B1qzTnTW/I3mzReNmzfXvOMWkw2ihyHuQ/v5WmDxrmyis0VfD+PISai/ICcSrHlc8PI5PyfvFfRhHMnHtIXFu7OJ8uQk+tx6pZpTUL8nJxKs2Vbw+NaIvDHfOWLxpOigaEbIdQQP3pNNdLbopnt6EGU/w5otBe928l6bHxk2z8VbrWN4wN5sCu/QOhGh5/fTKov/9OnNmk0Fjx86kZfmO3G+maK70Hx8lbaFxfuyCf0HSo3TW57i3Ph70UTySvDYzQUv/9O8h2MvHHOxEXork1dkDrT4WE4YzPF14Bw1L8Jt9jXE06A1C4NXgk2zLn/Y0HuUvA/mOxyPh9i9tlyCXr2noif2+wL6JRWZhV9X/r7oE3RRGebY2GVo/fqp6RZ4vufQuZ9Bj+2H9uD9+E7h/ex9cpuvgM6xzH6pb6IlVl+pVCqVSuUf4geL6L5FJgxKQAAAAABJRU5ErkJggg==>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD0AAAAZCAYAAACCXybJAAACYElEQVR4Xu2WTYiOURTHz0jjq8SCpmwkNlYmSTEiWcpCw0pZ2GArSzYWFlKEKSILNTYWdjJjpdSw8JWPjZrENDEi3x8x4/y75/B/z3vmo1m9dH/1773nf859nnuf9977PCKVSuV/pUv1RjWmGlDNaEz/4ZDqg+qLak/IOctVt6Vc60bItQynVD0UY0IY8DLywBNVP8WPVLcoBhul9HVWhbhlwKDWJh4Pdn6IHXgLQryPYvBDyuppGeZJ8wRB9O6H2IF33tqLLcYv02d+S3FEtT54cdIxdtg/TG3mouS+s0F1QHVWyqrBeYLz4oSUFebsV/WqNpHnYCteUz1W7ZVpriwMcjTE2cDZv0pt5ozkvrNLdVdKzWbVOfO3mdehGjRvkXnHLQZbVU8pXikT3y/loZROc8mbyqRvUps5KcVfEhMB1DxPvHjN78EbUV2mGMQ+E4IDDR3wRJns5oB9LL2s5rQUf2ZMBFCzO/Hw1mDem+8ctfid6qCqnXKTslBK51kxIVOb9Hh7+oLkfgQ1OxPvTvD8e4K5bp4LW21ScHjEC12i9kdpzgN4vp9wGCKe7umNmu2Jhw8d5rX5Dt9vtuqelDy/SlP40HJ+URv/QDZweKtDHAf+SfU2eBno25148Z/GHuaxoI3JMvDWBa8BfDygKBODGK8D55h5DJbZT4rbpNQsJS8Dg0Zd/LCB9yx4n8130B6k2L1xwYkaJ+r6SnVgjvl48g9U36RMKoIcBnZFSv2WxnQTuN6w6oVqSErfHapX5r2UvysF+xkxfCzzNVLu0Wm/EFbtCquvVCqVSqXyD/EbbCXM10D3aJQAAAAASUVORK5CYII=>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAaCAYAAADBuc72AAABe0lEQVR4Xu2UO0sEQRCE2wdmgqhgIggiqPhTRAQDAyMTY80EAzERMwM1EPwBamAkxgomBgZm5j4yn4jiI9AuetbtLXbkDmRvxf2g2Jmanttitm9EKir+BvuqzzrUMPDyyRyPQw3leIXRKXainmaxQGfkgws2iuJA1UTenFjQcfLbVKvkFcYsG8q95H/iDlUPm40krz9LR4tYyFNecLSKtQHo9gtFMi8WdJQXApeqflWf6k3Skx8I4xPVURifq47DGE+A8bXqMIyfQ/1DmNfMk8Q3jKjWyEtqx1Rd5A+7+V14rjgPNbtujkOoGWyOBV1UXZGHPx7Al/DgN3DvJnyEZ6/zULPj5ktu/CPoO2yO9Wdyv0KbYrdADA6aBwetmS2xzdPkexD2VtLAC9nlb7A2yCaBmm02Y0yoXsQ+IQJA6NN3ibdAwpTEa349aD2ssyElDbqhWiavtEFxRb2q9sRe1J6psLsVV9GNpG3E4E5Fq6EGelTNZCoqKir+OV8FGXN2xTdAQAAAAABJRU5ErkJggg==>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFwAAAAaCAYAAAA67jspAAACaklEQVR4Xu2YsWtUQRDGRyO2SkRsrKxM75+QLgRBRQSbNIKgEBEhbSCF2ASDhRjFSlALERRrlTQWgoKFjSSYkE4TJVGJJuh82Vkyb9jd7LvkipP5wcfuzuy+2fvybrMckeM4jtPrPGf9bSFnh8DEs4mYNfd4Iua0pJ/CG67ZS8HY9yYO5m3AaccL1h4Tu0LB8JMmvp81aWJOS0ZtgFmm9NFxkHXEBp2dkzq/nS7RR8HstzbhdIcxCoYP2QQzxfpBIX+bNdBM003WZwr5u6zhZnoz/5FC/oDJgTkKuXusQyZnwbxF1kvpY1+vWN9kHOdsyJwlGaMf9wAesL7I+InotYxHZE5NrY5ZofJDnlE5f5XK+XOsadYbm6DwRy6t1VxXfax5rMYL0q6q2A1qPvui6uf2fF/amlodgwemikd2w3Bg51yW1sZzHFV9rHmkxuPS4psSgWn62fto6wJg93xG2k/S1tTqCFz78MDS+Q3D8TXNYTdviYavU/PIiW98aW0Oa0IKa7jG7jkanaKmVjU4d/HAERPXwHCYlcNu3hINP836LX28bbhygtLaHFjz0AYNNYZ/YP2i7Q3frlaRU6yfFO7eX0U4x2FGaoMpww+rfs7wE9JGw0Gc9zQRa0ONCTWGR7pqeFtSR8o11bebBzAbPxcAbfg71i3WhIrZtTXUmNDG8BI1tXYV+08T1zs9tpuH0WtqfF71cfWzH9SOa6gxoScNR7GcavI4pnBk4fi6JLFZafEhEMedGPfbYxIvMUNba6DvrAuNGUSDEkddzMF8/QPcHwp3dORRF9fHFDW1ep47GTmO4ziO87/zD7Zb5qOFe0JdAAAAAElFTkSuQmCC>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD0AAAAZCAYAAACCXybJAAACZ0lEQVR4Xu2WS6iNURTHl0ceE0mRuhOJiYFnJh5dXUaS5DVSBiaYykQxNUBxcwcXNxNRMjAQeYyUwsCjPCbqJiTvPENe699ay/2fdfc97jU6tH/173zrt/f3fXufs/f5PpFKpfK/MkvzSvNTc1UzvrH5Nzs17zSfNJtSWzBNc03sWpdSW8uwWdNJ9TGxAc8lB+5pLlJ9R3OFatAudm4wO9UtAwaVB5bduFQHcLwqUG+hGnwVWz0txWPpP6E86VupDuCO+PEkr/HJXHDf0uwQG+RycvlLCNjvomPmqJR9sFizTdMttmqGi/1f7BdbYcFWzXHNEnLBVM05zV2x7TqklbVKbIAHkh/MpE/TMdMlZR9s0NwQ69OhOeR+pbvJml53E93t8xqs0NyneoY0v18DezUnNd81S1PbYCZ9mY4ZfIHwbbkhgT4PCy5f80tyLzQnqAb5nD+CweGkM+RKNwfssfRKfQ6K+ZG5IYE+GwsOTw3mrftgt9dvNNs1o6htSORJ5jpgP9Ce7pGyz6DP+oK7ntxL98x5dxFstaZgOR9OLk5e5PV7rzNwsZ8Wev23/97os7rg8KLDPHcf8P3GaG6KtQ/0giVrpG+CTLgRXuMXyH0A3LxU54F/0LxOrgTOXVtw+ZfGHuax4BiTZeAWJNcAOoymeqa7s+QAHB4HwR53DJbZN6qHifWZQq4EBo1++cUG7kFyH90HOO6lOlxTJmh+eGK/4DGTGSt93/xtzWexSWXQhoGdEuu/rLG5H7jeU80jzROxc9dpnrnDy1OsFIwPNTyW+Xyxe8zxTwTzmO79K5VKpVKp/EP8Aog3y/WOTHI0AAAAAElFTkSuQmCC>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD0AAAAZCAYAAACCXybJAAACbklEQVR4Xu2WTYiOURTHDyaxkc1I2UhEViPZkAxZykJYTVnYYDVoFvK1QBaTQiyIpETKwk6DlVJYMFMzbNSkmUm+8xny9f/PPcd73jP3nXnHxkv3V//mnv8993nOnffc53lECoXC/8h26DK0UOMF0AWo/XdGhb3QO+gTtDnMGXOhu9BP6GaYaxgOSirQ60FVRuIhdMPFvdBtF5MVktYbLSFuGPZDx6Hz0B5oUvX0MNMkXzy96SHe6mLyFboTvL8ON7oymoFuqb3pMzqeoTH/eq6r31DslrE3bW0f8f4+N/ack7xvLId2Qqckdc1ESc+Lo5I6zNgGXYRanWfMga5BfdAWqaOzdkGHJBVmBbIATz2bvurGnpOS94026L6knFXQafXXqjcT6levWb0jGpM10CMX84E82v2G2QF1BY+LDoQ4dyHv33JjzzFJ/qw4EWDOk4wXr/kleC+gSy4mcU1dxJvF2PA+Wy+Xc0KS3xQnAszZlPH41vC8Vd84rPEbqAOa7OZqMiEa4LuMf9O1zvRZyfsR5mzMePeC91J9DzvVaqF41EaFSa8ynr/w+xAb9Ow8LdP4T5/ezFmX8fih43muvuHvN0XSNwbn/at0BExgW0TPX5i/QK5weotDHAv/AL0OXg6uXZ/x4i/NM+xr4Zib9dBbGrwq+EnJp6LRKmnRfOcRenwdGJ3qedhm31zMo8Oc2c7LwaKZFz9s6D0O3kf1DY77XWzemLC9mWjiey8yVSr/+R7os+SfB5xjYVck5a+unh4Br/cUGoCGJK3dAD1Tb1AqncLzzJg+23yJpHss0r/UD2ie5hcKhUKhUPiH+AWiPskEG5Bf7AAAAABJRU5ErkJggg==>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFsAAAAaCAYAAADYMiBQAAACyklEQVR4Xu2Y26uNQRjGX8eUG3Hhdt9oE+UCyaVwIVuiyI3a5cqFSOTKvyDHhE05FClukMO9C4UkIUpyCOV8PuTwPr0z1rses9b3fdb62u3Mr57WzDOz5vveWTPvzN4imUwmkxlqnFb9qqBMB2ACVyQ8ntjJCS9TgfFiK9szXGxSr5MPHrKRKc9Z1TDy1otN9hLyR6u2kpepwDo2lNeSThfjVBPZzHRGKl9namCE2ERf4YYEa9gYopSNY4rYedY1NotN9iJuSIB+I9kcRKaqDoq911HVPtU91V3fKUFRHA9U11QzVdNUd1RffId/5b2USyGLxfoNcEMNLGSjAH7/nQkvUhTHJ9UBNqX1eJUom6/fSmMX1M0zNgrgd1qV8CLt4sDuTvngIxtVwdUOg5fJ13EloD++x3xVnVRdUu1QPQ7+LtUh1SPVsuDFH3i56ojYdyM/XXurwBnu90R1mLxIuzjuBz/FJDaqsl9s8H7ymaXSyHGYDA7klmpOKGOy14Yy0sGrUAY+EJSRD8EWsUn3bVVA/xNiPzbK85qb/1AUB777g7yOwOpCXsLd+mUQ8vY3aR3kB9VusVWKg4P7YYz+UL4sjWCxmt+FT4gnO7JJdd7VefwiuD/q+BuBKYrjVMJDHXODA5LbagE7wIOHjnH16aobqquqc86/LRZcCv/iGyQ92T3OawdPAurbyQNFcUwIXuq6x8+oBRw2fE3CFjzu6mdUo1w9Mlaat+VqV/Yvv1F10dXRhvv/Aue1gycC9XjIbgufZeIAx1TPyZslfz+j63xWvRA7wSPYTsjDSB3YlgD5Gi/jFelRfRdb5TGvI7VgXHxiojEedCG0zxB7Dk8Eg2vcG7GxkBbjla1X7B2QnuZL+TgifWKL5KbYe+P+vrKpxyDChwr+fbuHvE7Y20LY9v8dT1VzQxnbH6sldUBlushsSefuTCaTyVTnN6pD2SExDfN8AAAAAElFTkSuQmCC>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAZCAYAAACsGgdbAAABr0lEQVR4Xu2VzStEURjGDwsfKYlI2SkbC6EkQmIrRdigWShhpWRjaWOlZMcfQHZWxF/gK1bYqElIPiILxcLH+3Tec+fM43axmlncXz3NPb/3nbmnc8+5Y0xMTPZSJNmVfEkOJTnp5cxTZezkCnVcpuPcoCMLeJVskDuSvJHLKFi1IXJz6rOCDmMn00Y+ob6UvKNdMiNZkZQYuzXGJEuSYq9vSrIm6fSco1qyLTmVTEj20ssppo2dTCP5QfXN5B0jkmNje7okq+p71VVKkurK1S3qGPRIzr1xrYl4cvPGFuvI96kfJs+g5zLE8Q3fyT1I1r0x4O8EjBtbrCc/oL6bPIOeRIg7I/ei3rGg42fJrCTPq/3A7ckW8qPq8XqKAj186OAOyD2q99lR57KZXk6Rb8Jv9NfTjZ7+ELdP7l69o8K7LpCcGFvHIQwFxWVyW+p/Az3YGux4JbEH/d/DNSbnA9dKLiBs1cJWiMFN0DdJHu6CHP4weJJJb+xcJDhpH/qJZryaosBK3UquJDfGTgKvrTt115In7cV+xBgej73J2Hs06CfyKanR/piYmJiYf/AN74J3q/FQiSIAAAAASUVORK5CYII=>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE0AAAAZCAYAAAB0FqNRAAACsElEQVR4Xu2XS6hOURiGP2HAQAaYSLnlllyiiAHKTAwMTGRkwsStDOR+nJOBS4gk5JBIUcrIpZRSmBxKTIyQpNwvyfW871lrnfPtb6999qLUOb/11Nu/33d9a/97rX/tvfYvkslkMo3HeugCNMn7CdBZaF1nRRdboQ/QF2ilaQuMhe5Cv6Ebpq1haBY3QK22QoXjEXRd+YfQbeXJPHH9A9OMbxi2Q4eg09AWqG+xuYNBEh88s8HGr1aefIPumCxG7Pw9Fk7UAhsa7kt8UMxO+ONh3vNTc83ndaTU9Bg2S/2khdvWovNt6lhzSuK5JaXGshzaCZ33fgS0D1rRWSEyBNrv834qD6yFnkCXxD1ODhSb42yCWsRddBjgsUJF2qRdVseaIxLPLSk1Fm5M4Rr4vB3t81fQd2g3tMpnnDTW9fGevIUmK88NjJtiLRugqybjyXcZHxuUzm+pY81Bcflw22CI9U2BOz37ht2fTPfZGZURZmuMH6g8SZq0GHaSrA/o/Jw61hwWl4dbYww0MyLW2IziLdcdrVL+3ok+s89XZjuMp25Ci1Rei16ugZ/y55NW9Uw7KcV8FrQkItbYjJriulXCjch+L98VmdlVxKxJ+f7QL58HjVPtlbDwdSTTF/LR+ACzx/54rvf21/3Xu+dxKfflak6ZNL5KBaZKedyVsGhjJNOdlxkfYDbD+KXKk0/QG5PFiJ0/hVYp9+1updlntSa8NtXCv0RDlZ8vruN4lRFmYScie3ym4YbyQ3ne+qwZqbIq7LlSuSLlvnN8NsrkzI4av1j52ZL2A3fA25MnCApbt2aAuLZ70APoq8Sfh2z7DF0UV7+w2FyJHXgK76Dn0DPopbhVxOt64TN+clHwFmY7M9a/Z2fwFNorXePm2HoVfzNp/z2x/7yZTCaTyWR6Pe12xNabOXqiJAAAAABJRU5ErkJggg==>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFcAAAAaCAYAAADCDsDeAAACq0lEQVR4Xu2XS8hNURTHl0ckkRgYiJL3UClTpRgIpcjAQEoYeMyMzGRooOQ1JcrAQGbkE0IRA3mOKKG88n6F9W/tnf+3vn3vuefec7+o9at/Z+2199nnnP89Z+19RYIgCILh5qzqdw0FNYBh6wo5b+T8Qi5ow2SxN5cZKWbiHZcHT30iaM051QiX2yVm7mqXH6Pa73JBG3b6hPJWyp//JNVUnwzqUaq3QQOMEjP2pu/oE9MpnkDxv8Q0n+iW3WLmrvAdynGxvgHV7RRfUt1I8dI0DvE91cUUP0/jvqt+pTETVQ/EFs9Vqluq7amvFbPF5rsudg+I76supxhHgPiD2PV/pjbiZykGJ1P8SXVadUZ1l/rBWtU+sXs8rHpEfV2Bm+ILMDAgM04Gjxut2iH29i2nPMZsc23wknJgvVSbu1I1hdqYawG136TjNcrhh+drnaL4veoCtcEy1YwUex/wMvQEJvSTZr5QPFaGjjukWuxyGLOV2gOUX0h5UGUuvioGc2DvnfmRjhsoB6NfUHsJxTD3PLVnpWM+3z/fIteuBbZamLCTelsyt4Q3N3NQrA8Pvtn1dYo3t4Q3l2Fz8SXyjwK+il0Db38ueV1zTGyyjS5foo65W3wygX10/lKg8YO7K8E583zSAXNR80vAXJRB1G3M5c0FJ+Tv/WGLWos1qs9iJ75OwgWx+LQzrwlzmScytA5X0YS5XBZK5mbyLorXj77Rq7n+bzT+hncyH9OEuX5BYza5Nv6dopz1nV7NRR5vQwar9FFqd0IT5mKL2Iq8bcxcVc10ucb5KFY+Xoltf3gXkcH+EqUGYzAWDzKH+vHAB1SPVVdUD6mvim9i181zo4x59qreiY2BEGOfnsH+lssgFjTPHrF6jH01xmHO/5q5qiMtFARBEATBcPMHXfHS/72R3v4AAAAASUVORK5CYII=>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIIAAAAaCAYAAAB7NoTTAAADl0lEQVR4Xu2YWchNURTHlyEPRChjUSJDXiRkfhGSpCRPpkwPCIVM8ZUpJOWFhHyIBzKUDIknUSSUISmZ5zHzzPpba3XX3c75pu69vu63f/Xv7v1f5+y7zz7r7L3PIYpEIpFIJBJJ5wjrdyUUKVJwc8ckeOFN75zgRYqEpiQzgqc2yQ2/EvjgfmhEioOjrFqBN4ckEUYGfj3WhsCLFAmzQ4N5Q8lLQGNWi9CMFC9J+4NIDaMOSRJcDAORmsUCkkQYHgaqOdjYxlksh7yn3A/o2tDIE1Xpd6H6li/2h0auyMf+4Fdo5Imq9LtQfcsHvSlPiYDXw7L2B5YkXVn7WN9JvkMYE1inWWdYy9Wzc3yCWfmpKz9krQmOw4VeIGnrsnoA8Z+s21r2vv36dtIoq28rWc9YQ9XHtU5nvWL1V68lybEvWMdZB0j6ZOwkuabDehyw9vHt5iBJIjbSGNjM2sraxVqq3iKSc1aQvO4/YpWoZ+qkx+YEdACNTgx8D+IztDyA9UDLeK20iwVpZQMePlxZ2cDgg/qB34t13tUthoELvef077eRNNL6Nog1jNVGvY+ZcNY5bYP6D1YHLXv/kyt7v4mrzyRJAOMYa4SWF7O+aBlJCkoohzPCKJJO4tsBsh3CPuEbpQ+S0ZMyndvN+kqSGBCe2I4aS2qnlLWJ5C3lBMnTBvrq7zbWWS0bvp2kNuGhD7iJFSWtnRAk7XrWDcqOtw7qSBjMZOAuSQzj62fOsH3Um+nvYOfjgbMEXMja62Igp4lQWfxFdKdMIuDJvO5iHjvHv4nYaypuOMAUuS4Tpu2sa64OKpIImAmSYmkk9S08vw9l7yV8PJwJ31EmERqQ9GcWld131Jvr72jnzyOZYQASoTQT+ssy1iEtT/WBQuAvogfJzGH4WBeSgfD+Kv014J905asuVlc9YxLJ3sMIBxOYh0HB8lARkvoWtn2JtUPLlsCttI6lwx//gTKz2mPn2wMD/PHdXH0c65SL3WEN0fISyl42AK4TezKApCgYmKZest6SLAu2nNj615D1muRJnqweGEtyLDLcs5pkjQTzWe1cDKCOqf4ea5rz8f+2hIUejj9H0g945RH27TNJO/DG20Ekm1m0u5HkybxFsizYGOB/rQ/w+pFs7LCRfELZ+y7c+D0kN91vLsEUkqTBmLZXD0mA64H8gwduqiLlMJe1JUX/i3DGidRABpIkAt6CIpFIJBKJRKo1fwDIHSQmKIBB2AAAAABJRU5ErkJggg==>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADMAAAAZCAYAAACclhZ6AAAB/0lEQVR4Xu2WwUtUURTGT4RUkOEm/wBBFAUhXUdjunUhiG5FXejOAqHSSKjctHOXBSW4EVy0Ld2IuHGjQlRgiyGtCJEkIdpEft/ce8cz573nQIgzi/uDH8757rnvveu7782IRCKR/+EOXIQtvm6GC3C82HHCQ/gL/obDZqwqeAL/GTdLOhwf4LKq38N1VVcFj+AsnIdT8GLpcIFr4hZpYVZnw0rCBXTa0LAl2Yt5acNKMinlFxO2nyUrDwzCGbjk61b4AvaEBtAE5+BTlWmm4Rf4GrbDPj1ouS/uQLyoV/7v85KO7IvOygP6eczDWnjB17twFd7yvfxsj8WacwI/4ZiqE9yFb03Ggzw2tT0Ryco1e+J6LquMb1BmQyojzNpMrbkhZRaThr1IWweyck1ekj28IJsRZjlT0zfwpsoz4W23/JWzW8xnSfaMpGSE2W1V1/tMe1WNJ2DDQUqmT3Zk6gCzjzY07EhyLr9wbUbsYi6pz93ixg9VloANEymZPlm/qQPMOmxoyEty7ml3pkvVfOA1vZI+rwh/mlxXdU7cBL4yNcxGVf3MZ+XYl2TfA5/VqIzbh9mAylg3qvoeXFN1Ktxm4W7QhtLhAlfEjW3AbfhH0p83DY/Ltxlfwz/EbRVu2a8++w7fwU/wm884xn8wWRH38Ifr4m/ISCQSiUTOnWMF0Z1YT5MAxQAAAABJRU5ErkJggg==>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD0AAAAZCAYAAACCXybJAAACWElEQVR4Xu2WS6hNYRTHl0cYyKO4KZREyYiBCekKAwMZCAN5DEw8IsKQ6Z1QFIqSGQMGRkRGQhiQAUp080oeeRR5JPz/rbVu66z73XMOJoe+X/3brf/6f3t/3z7f3meLVCqV/51d0KZsGu+htdBYaDS0AnrXkFCmQTegn9Cl1OsYTkHfRCdJbW5s9+H9qEkNCZFu851Zqe5IWi26BzoCLUo9h5m8U3hDryevo2i16GZ0iWZ4jFw0v2P5m0XvlXLmhJR9Zz60EzoKjYEGQxugA9CokOO8TkILgudMhc5Dd6GN8ps7q9WiH4ie+Br0HRoa+mctkzksZd9ZA90SzSyEjpm/zLwJUK95483bbzVZCt0P9Uxpfr1+MLwlmwZ7w0N9zjzncqqdg6L+xNxIMPO44OVzfk3ea9GXcSSPaQrDW7M5ADNE83us5tYrXeyQqB93RQlm1he8e8n7YL7Dlytr/n3uhoaFXltw8LZsGkNSzWePed9aAz3Tx6XsZ5hZVfBuJu+N+ZEL5rn4qLUNB2zPJngo2hsRvJHmXbF6ntV/+vZmZnnB44dO5JX5Trwe53dbtM+XYlswvCOb4An0KXlLRPOrg1ea+EfobfJKcCy/8rKXf2k+w3HR+cdwb27yiowTDe/LDTAZepS8L9Dn5HGb8a3uDBI955TgleCkmcsfNvS4yyK8+XnRvaF2rymnRe/eM+ipHV+KfklF1ome7Lkdrza2+7gjOrEzornFje1+8Jd8IXptnptjV4rOwefjO4XPs8+T23yO6DVm25H6AU23fKVSqVQqlX+IXyi0tvDB3Ce7AAAAAElFTkSuQmCC>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEgAAAAZCAYAAACSP2gVAAACt0lEQVR4Xu2WS6hOURTHl2ekJImBwTUw8UhkJHSFiamBkYFi4BFRhphQbuGW94Qkr8SAUt4lpTBCIpl5RfK63Ov9WP+717rfOuus4/ticgb7V/++vf7rnPOtvb797X2IMplMpl6sZ63wpmEjq4vVw1rqcsp41i3Wb9YVl7PsYH1jvWHNcrlacYJSoZgQtLKY7uMB67KJ77NumBi0U3qGMtXFygfWFhN/ZnWYuLZUNWg4xROFN8LFfgWi+TdNPI/KzxoZeLWkqkF3KJ4AvAMyHi0xPi2XxFd0tXrgLfZm3ahqEPyqSam/yYwth6joY/zdxAr8e94U+rGWsbaxdos3g3WUivvXbNYx1gbjWTpZz1m7WAtYbcV0c/6nQWfM2LKXyg3CRu+Bj70oYjClyeGaR5Q29v6sIeKdY72kxoTfim+J4gnOawpuWuVNaq1B183YspOSP1ZijDEBT9V3WKJrzoqH01PB6rLXTXIxWEf/2KDV3qS4MGD942Zs2UPJHygxxu8b6T7g//KmI6rjZOBNCzy99zBrisu1DB6wxpsUFwasX7UHHaSij/FXEyvwH3vTEdWBfch7k8XD31CZLp7qp8m1DG5c603mI5WLAPAeynimxM1OsWiSAN5+bzqie48E3kTxtEHY5CFlCaX8NeO1BG7Cf9OziMpFAHj4ZWy80MTgExX3nH1UfhaKhzfI+Z6oQdEK0j1ngMTtrAuNdC/YG6sOhZBRlB663ScE5JabGEeuL+wi64eJdeLjjAfgYRLKbYpPNk/UIL9CwVzxxkg8R+JhegFznrXZxJWcYr1mPWM9lc9XlF7oLEMpfQkmc5f1hYrLVkGum3Wa0vXzi+le2ijlrrKeUHo3+Rt4k0eNqA/CGJs+NnutG8c83n+wKvA8eC9Y7yg1aCul2rTJiDOZTCaTyWQyAX8Ad/HnXuI9p9IAAAAASUVORK5CYII=>

[image22]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEgAAAAZCAYAAACSP2gVAAACyElEQVR4Xu2XS6iNURTHl7ciIjFA18DAK5GR0L1hwFRGQgYmiChDTCjKo7xHkrwSA0peURLCjJK8Jl6RPCPvx/rftda9a6+7z/1OTM5g/+rf+dZ/rf3dvdfdZ3/fISoUCoXGYjVrSTSV96wFrAGs/qy5rHdJhTCSdZP1h3Ux5DxbWd9Zb1hTQ66hOEoyUSwIWpqm27C817CkgqhZfWNCiI0PrA0u/sLa5OKGpapBG1l7WDNCzkBN3IFo/g0XY2xs2sCM15BUNagzBpPU4NNzQX3DdmsE3vxoNhr/06B1lK/ZT6mP6x8uNuDfiabShbWYtZm1U73JrEOUnl/TWIdZa5zn2cZ6ztrBms1qStPVVDXoAesu6zrrJ6u7y5/Umshu6tigjy424OMsytGTZHGouU9ysHdl9VbvNOsltS/4rfqeXDw6eJVg0LJoKsj1cvEZ9YwrITa2k/hDNcY1FhCBnxvvydWcUg9PTwO7y9eNDTFYRf/YoOXRrMEokvq1Gh/ROLKLxLfdhmu8MkTg/45mINegYxlvYsazsQdY40OubnCDFdFUuoUYWxz19zSudQbto9TH9TcXG/AfRjOQaxDOoeiNUw9zNCapZ/rlcnWDgSujyTwiyeE7b/RV76rGUzSueorlFgng7Y1mIDf2YMYbo541CIc8ZCwiyV92Xl1gEL6bkSesz8GbRVI/z3mI57gYfKL0zMF7VFwQJg+vR/AjuQbldpCdObbrm1nn2tOt4Gys9VDIMojkpltighnOehy8r9TxD5wneboZtvARzgPwsAjjFuWfbJFcg+IOBdPVG6Jxi8Z9rIA5y1rv4pocZ71mPWM91c9XJC90noUkfwTvEfi8lqbbuE2y206Q1M1M0600keQukexO3LMz+pHMEfODcI1DH4e9zRuPebz/4J+G+8F7QfJ7sYXkVwDmZk1GXCgUCoVCoVDI8BfZleAJUspskwAAAABJRU5ErkJggg==>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAZCAYAAABOxhwiAAAB00lEQVR4Xu2WPyiFURjGnzLIQDIYWBSDiTJIEUUKIaUMMlFSyGBQBmW3UCYxyWBGZpMyKMlAWViUP6GQ/+/rPefe873O/b771S2l71dP3fM+zznn/brnnvsBCQl/xgxpjTSo6g1qnDNqSTekL9I+qThoR/IKmbtB6iB1kl5IzZB1J9JRnBuP8yz+fEe6JT2b2kEqHcIYackZr0Mm1zm1TBRBslfaMJxCfLdxi21cU4DMXgBfyFfzkU0ubuOMfeABbbhc4vcCYYta+DxzZlUbihPEb/wQ4vFpyJpZyKQubSjeILkqbShGEb/xMM9LH2TCojY8xF5cYedXGlWTekztyMlFskDaJH2Q2pTnI1eNtxq1Q77lY9I7qSKVzJJyyIJb2lDYjUu1QXSTGkn1Rnwt9gYS4Q++DfH4BMQibFEL37WcGdIGMU6ahtzNnDkzNZeoPaL8n6Oxomp2UpOqu5RBMk/acJiHZKa0gejGQv1++AO2lqfqml1Ijo+FD/7dsD+pDfj3tYxAPP5HzQgH8p1xjantOLUw9iD5OW0g3Vyc69A27fMClJA+ja4hE5YDiWhaSA9Ib8ji9xdeu5A0nI7iXuVYfIvwO8sj6QLSfEJCQkLCP+UbKjWdiPyfM8kAAAAASUVORK5CYII=>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAZCAYAAABOxhwiAAAB10lEQVR4Xu2WzysFURTHj6wsWCgWVkKRP0BK+VUKISsLWVFSyK8kEQk7KzsLpKT8AYqtrYWSLCgbKwuEQn7E97x778yd482dN1JK86lP3pzvmXvPe6b7HlFCwp8xBTdgt6hXi+tfYQzuwkp9XQG34ajXEc0r/IQ7sBm2wBdYC2/gkN9KlzrjfpZf38Fb+KxrR163gyXyFzEeBzrCySPVfy0DzTmp3B7cYPaS5FB4FmAersItOAuzg7GTTDaIOzhj3nCXDGx42AZZzAB+nnnxdRkIzij+4Pwf52xABjYz9LPB30gtXiYDQT/FH9yVeUzDZVKNm/rvWqAjPRkt7sDcX6rlQ6Fd106svlDG4YGo8c2Loib5rcEbtU2wFZ7Cd1jsdcYgk6FMT6EMQBusgVVaPhY7Ah3uPfZIZZ0ysMmSBfBB4Ysa+Kzlnh4ZgEE4Qeps5p4LXbNxDc5E5amQvyRkzXkTKCLV8yQDiwVSPSMyoOg9ovJUOJmm5rxJs0+qjx+LdKyQyodlQO49+khl/I0aCn9iBdZ1Pambyq2ai0NS/XMyIH+4OMehGTpd9g1+VEwzWxKMI6mDDxRcg3+/5MNc2Ou30r3oY/kU4d8sj/CK1PAJCQkJCf+ULyk+mpdNwh6rAAAAAElFTkSuQmCC>