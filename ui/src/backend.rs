use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

// ─── Data types ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConnectionStatus {
    Connected,
    Disconnected,
    Connecting,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureEntry {
    pub feature_type: String,
    pub label: String,
    pub user_intent: String,
    #[serde(default)]
    pub parameters: serde_json::Value,
    #[serde(default)]
    pub timestamp: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoryEntry {
    pub timestamp: String,
    pub command: String,
    pub action: String,
    pub result: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum ServerMessage {
    #[serde(rename = "status")]
    Status {
        solidworks: bool,
        qdrant: bool,
        ollama: bool,
        claude: bool,
    },
    #[serde(rename = "listening")]
    Listening { active: bool },
    #[serde(rename = "transcription")]
    Transcription { text: String },
    #[serde(rename = "action")]
    Action {
        command: String,
        action: String,
        result: String,
    },
    #[serde(rename = "features")]
    Features { items: Vec<FeatureEntry> },
    #[serde(rename = "waveform")]
    Waveform { samples: Vec<f32> },
}

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "type")]
pub enum ClientMessage {
    #[serde(rename = "command")]
    Command { text: String },
    #[serde(rename = "listen")]
    Listen { start: bool },
}

// ─── Backend client ──────────────────────────────────────────────────────────

pub struct BackendClient {
    url: String,
    status: ConnectionStatus,
    listening: bool,

    // Service connectivity
    pub solidworks_ok: bool,
    pub qdrant_ok: bool,
    pub ollama_ok: bool,
    pub claude_ok: bool,

    // Data
    pub features: Vec<FeatureEntry>,
    pub history: VecDeque<HistoryEntry>,
    pub waveform: Vec<f32>,
    pub last_transcription: String,
}

impl BackendClient {
    pub fn new(url: &str) -> Self {
        Self {
            url: url.to_string(),
            status: ConnectionStatus::Disconnected,
            listening: false,
            solidworks_ok: false,
            qdrant_ok: false,
            ollama_ok: false,
            claude_ok: false,
            features: Vec::new(),
            history: VecDeque::with_capacity(500),
            waveform: Vec::new(),
            last_transcription: String::new(),
        }
    }

    /// Poll for new messages from the backend (non-blocking).
    /// In production this reads from the WebSocket; here we maintain state.
    pub fn poll(&mut self) {
        // TODO: integrate real WebSocket I/O via tungstenite on a background thread.
        // For now the app renders with local state.
    }

    pub fn connection_status(&self) -> ConnectionStatus {
        self.status
    }

    pub fn is_listening(&self) -> bool {
        self.listening
    }

    pub fn send_command(&mut self, text: &str) {
        let entry = HistoryEntry {
            timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
            command: text.to_string(),
            action: "pending".into(),
            result: "Sent to backend…".into(),
        };
        self.history.push_front(entry);

        // TODO: serialize ClientMessage::Command and send over WebSocket
        tracing::info!("send_command: {text}");
    }

    pub fn toggle_listening(&mut self) {
        self.listening = !self.listening;
        tracing::info!("listening = {}", self.listening);
        // TODO: send ClientMessage::Listen over WebSocket
    }

    /// Apply a message received from the Python backend.
    pub fn handle_message(&mut self, msg: ServerMessage) {
        match msg {
            ServerMessage::Status {
                solidworks,
                qdrant,
                ollama,
                claude,
            } => {
                self.solidworks_ok = solidworks;
                self.qdrant_ok = qdrant;
                self.ollama_ok = ollama;
                self.claude_ok = claude;
                self.status = ConnectionStatus::Connected;
            }
            ServerMessage::Listening { active } => {
                self.listening = active;
            }
            ServerMessage::Transcription { text } => {
                self.last_transcription = text;
            }
            ServerMessage::Action {
                command,
                action,
                result,
            } => {
                let entry = HistoryEntry {
                    timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
                    command,
                    action,
                    result,
                };
                self.history.push_front(entry);
            }
            ServerMessage::Features { items } => {
                self.features = items;
            }
            ServerMessage::Waveform { samples } => {
                self.waveform = samples;
            }
        }
    }
}
