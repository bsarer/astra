use serde::Deserialize;
use std::collections::HashMap;
use std::process::Command;
use std::time::{Duration, Instant};

const DEFAULT_PORT: u16 = 8000;
const CONTAINER_NAME: &str = "astra-agent";
const IMAGE_NAME: &str = "astra-agent";
const HEALTH_TIMEOUT: Duration = Duration::from_secs(60);
const HEALTH_POLL_INTERVAL: Duration = Duration::from_millis(1000);

/// Configuration for the Docker container, loaded from `astra.toml`.
#[derive(Debug, Deserialize)]
pub struct Config {
    #[serde(default = "default_port")]
    pub port: u16,
    #[serde(default = "default_container_name")]
    pub container_name: String,
    #[serde(default = "default_image_name")]
    pub image_name: String,
}

fn default_port() -> u16 {
    DEFAULT_PORT
}
fn default_container_name() -> String {
    CONTAINER_NAME.to_string()
}
fn default_image_name() -> String {
    IMAGE_NAME.to_string()
}

impl Default for Config {
    fn default() -> Self {
        Self {
            port: DEFAULT_PORT,
            container_name: CONTAINER_NAME.to_string(),
            image_name: IMAGE_NAME.to_string(),
        }
    }
}

impl Config {
    /// Load configuration from `astra.toml` in the current directory or next to the executable.
    /// Falls back to defaults if the file doesn't exist.
    pub fn load() -> Self {
        // CARGO_MANIFEST_DIR = .../tauri-app/src-tauri at compile time
        // astra.toml lives at .../tauri-app/astra.toml (one level up)
        let manifest_dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));

        let paths = [
            manifest_dir.join("../astra.toml"),  // src-tauri -> tauri-app
            std::path::PathBuf::from("astra.toml"),
            std::path::PathBuf::from("../astra.toml"),
        ];

        for path in &paths {
            if path.exists() {
                if let Ok(contents) = std::fs::read_to_string(path) {
                    if let Ok(config) = toml::from_str::<Config>(&contents) {
                        return config;
                    }
                }
            }
        }

        Config::default()
    }
}

/// Manages the Docker container lifecycle for the Astra agent backend.
pub struct DockerManager {
    config: Config,
    env_vars: HashMap<String, String>,
}

impl DockerManager {
    pub fn new(config: Config) -> Self {
        let env_vars = Self::load_env_file();
        Self { config, env_vars }
    }

    /// Load environment variables from the .env file in the astra-poc-vc directory.
    fn load_env_file() -> HashMap<String, String> {
        let manifest_dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let candidates = [
            manifest_dir.join("../../.env"),     // src-tauri -> tauri-app -> astra-poc-vc
            std::path::PathBuf::from("../../.env"),
            std::path::PathBuf::from("../.env"),
            std::path::PathBuf::from(".env"),
        ];

        for path in &candidates {
            if path.exists() {
                eprintln!("[Astra] Loading .env from: {:?}", path);
                let mut vars = HashMap::new();
                if let Ok(iter) = dotenvy::from_path_iter(path) {
                    for item in iter {
                        if let Ok((key, value)) = item {
                            vars.insert(key, value);
                        }
                    }
                }
                return vars;
            }
        }

        eprintln!("[Astra] Warning: No .env file found, relying on host environment variables");
        HashMap::new()
    }

    /// Get an env var, preferring the .env file, falling back to host env.
    fn get_env(&self, key: &str) -> Option<String> {
        self.env_vars.get(key).cloned().or_else(|| std::env::var(key).ok())
    }

    /// Returns the frontend URL served by the Docker container.
    pub fn frontend_url(&self) -> String {
        format!("http://localhost:{}/", self.config.port)
    }

    /// Check if the Docker image exists locally.
    fn image_exists(&self) -> bool {
        let output = Command::new("docker")
            .args(["image", "inspect", &self.config.image_name])
            .output();
        matches!(output, Ok(o) if o.status.success())
    }

    /// Build the Docker image from the Dockerfile if it doesn't exist.
    fn build_if_needed(&self) -> Result<(), String> {
        if self.image_exists() {
            return Ok(());
        }

        let build_context = self.find_build_context()
            .ok_or_else(|| "Could not find Dockerfile. Ensure it exists in the astra-poc-vc directory.".to_string())?;

        let output = Command::new("docker")
            .args(["build", "-t", &self.config.image_name, "."])
            .current_dir(&build_context)
            .output()
            .map_err(|e| format!("Failed to execute docker build: {}", e))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(format!("docker build failed: {}", stderr));
        }

        Ok(())
    }

    /// Find the directory containing the Dockerfile.
    fn find_build_context(&self) -> Option<std::path::PathBuf> {
        // Compile-time path: CARGO_MANIFEST_DIR = .../tauri-app/src-tauri
        // Dockerfile is at .../astra-poc-vc/Dockerfile (two levels up)
        let manifest_dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));

        let candidates = [
            manifest_dir.join("../.."),          // src-tauri -> tauri-app -> astra-poc-vc
            std::path::PathBuf::from(".."),      // if cwd is tauri-app
            std::path::PathBuf::from("../.."),   // if cwd is src-tauri
            std::path::PathBuf::from("."),        // if cwd is astra-poc-vc
        ];

        for candidate in &candidates {
            if candidate.join("Dockerfile").exists() {
                // Canonicalize to get a clean absolute path
                if let Ok(abs) = candidate.canonicalize() {
                    return Some(abs);
                }
                return Some(candidate.clone());
            }
        }
        None
    }

    /// Check if the container is already running.
    fn is_running(&self) -> bool {
        let output = Command::new("docker")
            .args(["ps", "--filter", &format!("name={}", self.config.container_name), "--format", "{{.Names}}"])
            .output();

        match output {
            Ok(out) => {
                let stdout = String::from_utf8_lossy(&out.stdout);
                stdout.lines().any(|line| line.trim() == self.config.container_name)
            }
            Err(_) => false,
        }
    }

    /// Start the Docker container with security flags and env vars.
    fn start(&self) -> Result<(), String> {
        // Build the image first if it doesn't exist locally
        self.build_if_needed()?;

        // Remove any stopped container with the same name first
        let _ = Command::new("docker")
            .args(["rm", "-f", &self.config.container_name])
            .output();

        let port_mapping = format!("{}:8000", self.config.port);

        let mut cmd = Command::new("docker");
        cmd.args([
            "run",
            "-d",
            "--name", &self.config.container_name,
            "--security-opt", "no-new-privileges",
            "--cap-drop=ALL",
            "-p", &port_mapping,
        ]);

        // Mount the data directory for mock persona data
        if let Some(build_ctx) = self.find_build_context() {
            let data_dir = build_ctx.join("../data");
            if let Ok(abs_data) = data_dir.canonicalize() {
                let volume = format!("{}:/app/data:ro", abs_data.display());
                cmd.args(["-v", &volume]);
            }
        }

        // Pass through environment variables from .env file or host
        let env_keys = ["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "DEBUG",
                        "DATA_PROVIDER", "MIKE_EMAIL", "MIKE_EMAIL_PASSWORD", "MIKE_EMAIL_PROVIDER"];
        for key in &env_keys {
            if let Some(value) = self.get_env(key) {
                cmd.args(["-e", &format!("{}={}", key, value)]);
            }
        }

        cmd.arg(&self.config.image_name);

        let output = cmd.output().map_err(|e| format!("Failed to execute docker run: {}", e))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(format!("docker run failed: {}", stderr));
        }

        Ok(())
    }

    /// Ensure the container is running — start it if it's not.
    pub fn ensure_running(&self) -> Result<(), String> {
        if self.is_running() {
            return Ok(());
        }
        self.start()
    }

    /// Poll the /health endpoint until it returns HTTP 200, or timeout after 60s.
    pub fn wait_for_health(&self) -> Result<(), String> {
        let url = format!("http://localhost:{}/health", self.config.port);
        let start = Instant::now();
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(5))
            .build()
            .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

        loop {
            if start.elapsed() > HEALTH_TIMEOUT {
                return Err("Health check timed out after 60 seconds".to_string());
            }

            match client.get(&url).send() {
                Ok(resp) if resp.status().is_success() => return Ok(()),
                _ => {}
            }

            std::thread::sleep(HEALTH_POLL_INTERVAL);
        }
    }

    /// Stop the Docker container gracefully.
    pub fn stop(&self) -> Result<(), String> {
        let output = Command::new("docker")
            .args(["stop", &self.config.container_name])
            .output()
            .map_err(|e| format!("Failed to execute docker stop: {}", e))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(format!("docker stop failed: {}", stderr));
        }

        Ok(())
    }
}
