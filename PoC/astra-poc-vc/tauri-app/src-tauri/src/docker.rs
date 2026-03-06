use serde::Deserialize;
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
        // Try loading from current directory first, then next to executable
        let paths = [
            std::path::PathBuf::from("astra.toml"),
            std::env::current_exe()
                .ok()
                .and_then(|p| p.parent().map(|d| d.join("astra.toml")))
                .unwrap_or_default(),
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
}

impl DockerManager {
    pub fn new(config: Config) -> Self {
        Self { config }
    }

    /// Returns the frontend URL served by the Docker container.
    pub fn frontend_url(&self) -> String {
        format!("http://localhost:{}/", self.config.port)
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

        // Pass through environment variables if set on the host
        if let Ok(api_key) = std::env::var("OPENAI_API_KEY") {
            cmd.args(["-e", &format!("OPENAI_API_KEY={}", api_key)]);
        }
        if let Ok(model) = std::env::var("OPENAI_MODEL") {
            cmd.args(["-e", &format!("OPENAI_MODEL={}", model)]);
        }
        if let Ok(base_url) = std::env::var("OPENAI_BASE_URL") {
            cmd.args(["-e", &format!("OPENAI_BASE_URL={}", base_url)]);
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
