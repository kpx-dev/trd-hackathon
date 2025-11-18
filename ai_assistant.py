#!/usr/bin/env python3
"""
AI Racing Assistant - Amazon Bedrock Integration
Uses Claude Sonnet 4.5 to provide intelligent racing analysis and coaching
"""

import boto3
import json
import logging
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class RacingAIAssistant:
    """
    AI Assistant for racing telemetry analysis using Amazon Bedrock Claude Sonnet 4.5
    """

    def __init__(self, region_name: str = "us-west-2"):
        """
        Initialize the AI assistant with configurable AWS region

        Args:
            region_name: AWS region for Bedrock service (default: us-west-2)
        """
        self.region_name = region_name
        self.model_id = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"  # Cross-region inference profile
        self._client = None

        # Racing-specific system prompt
        self.system_prompt = """You are an expert racing coach and telemetry analyst with deep knowledge of motorsports, vehicle dynamics, and racing techniques. You analyze racing telemetry data to provide actionable coaching advice to drivers.

Key areas of expertise:
- Racing line optimization and cornering techniques
- Throttle and brake application timing
- Vehicle setup and handling characteristics
- Tire management and grip analysis
- Sector time analysis and performance optimization
- Race strategy and competitive analysis

When analyzing telemetry data, focus on:
1. Specific, actionable feedback with exact values from the data
2. Racing technique improvements (braking points, throttle application, racing line)
3. Vehicle dynamics explanations (understeer/oversteer, grip levels)
4. Comparative analysis against optimal performance
5. Prioritized recommendations for lap time improvement

Always provide concrete, data-driven insights rather than generic advice. Reference specific telemetry values, times, and track positions when making recommendations."""

    @property
    def client(self):
        """Lazy initialization of Bedrock client"""
        if self._client is None:
            try:
                self._client = boto3.client("bedrock-runtime", region_name=self.region_name)
                logger.info(f"Initialized Bedrock client for region: {self.region_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Bedrock client: {str(e)}")
                raise
        return self._client

    def update_region(self, new_region: str):
        """
        Update the AWS region and reinitialize the client

        Args:
            new_region: New AWS region name
        """
        self.region_name = new_region
        self._client = None  # Force re-initialization on next use
        logger.info(f"Updated region to: {new_region}")

    def prepare_telemetry_context(self, telemetry_data: Dict[str, Any]) -> str:
        """
        Convert telemetry data into a structured context for the AI model

        Args:
            telemetry_data: Dictionary containing telemetry and lap information

        Returns:
            Formatted string with telemetry context
        """
        try:
            context_parts = []

            # Race and vehicle information
            if 'race_id' in telemetry_data and 'vehicle_id' in telemetry_data:
                context_parts.append(f"RACE: {telemetry_data['race_id']}")
                context_parts.append(f"VEHICLE: {telemetry_data['vehicle_id']}")

            # Lap information
            if 'lap_number' in telemetry_data:
                context_parts.append(f"LAP: {telemetry_data['lap_number']}")

            # Current lap performance data
            if 'current_lap' in telemetry_data:
                lap_data = telemetry_data['current_lap']
                context_parts.append("\n--- CURRENT LAP TELEMETRY ---")

                if 'lap_time' in lap_data:
                    context_parts.append(f"Lap Time: {lap_data['lap_time']}")

                if 'sector_times' in lap_data:
                    for i, sector_time in enumerate(lap_data['sector_times'], 1):
                        if sector_time:
                            context_parts.append(f"Sector {i}: {sector_time}")

                # Telemetry snapshot data
                if 'telemetry_points' in lap_data:
                    total_points = lap_data.get('total_points', len(lap_data['telemetry_points']))
                    sampled_points = lap_data.get('sampled_points', len(lap_data['telemetry_points']))
                    is_complete = lap_data.get('complete_lap_requested', False)

                    context_parts.append(f"\nTelemetry Analysis:")
                    context_parts.append(f"- Sampled Points: {sampled_points}")
                    context_parts.append(f"- Total Available Points: {total_points}")

                    if is_complete and sampled_points < total_points:
                        sampling_percentage = (sampled_points / total_points) * 100
                        context_parts.append(f"- **Data Coverage**: {sampling_percentage:.1f}% of lap (evenly sampled across entire lap)")
                        context_parts.append(f"- **Resolution**: ~{sampled_points/100:.1f} samples per second (professional-grade for racing analysis)")
                    elif is_complete:
                        context_parts.append(f"- **Complete lap data provided for analysis**")
                        context_parts.append(f"- **Resolution**: Full {total_points} data points (maximum detail available)")

                    # Provide key telemetry data points for detailed analysis
                    points = lap_data['telemetry_points']
                    if points:
                        # Sample key points for professional analysis (every 10th point for token efficiency)
                        sample_interval = max(1, len(points) // 200)  # Target ~200 key points
                        key_points = points[::sample_interval]

                        # Statistical summary
                        speeds = [p.get('speed', 0) for p in points if p.get('speed')]
                        throttles = [p.get('throttle', 0) for p in points if p.get('throttle') is not None]
                        brake_rear = [p.get('brake_rear', 0) for p in points if p.get('brake_rear') is not None]
                        brake_front = [p.get('brake_front', 0) for p in points if p.get('brake_front') is not None]

                        if speeds:
                            context_parts.append(f"Speed Range: {min(speeds):.1f} - {max(speeds):.1f} mph")
                        if throttles:
                            context_parts.append(f"Throttle Range: {min(throttles):.1f}% - {max(throttles):.1f}%")
                        if brake_rear:
                            context_parts.append(f"Rear Brake Pressure: {min(brake_rear):.1f} - {max(brake_rear):.1f} psi")
                        if brake_front:
                            context_parts.append(f"Front Brake Pressure: {min(brake_front):.1f} - {max(brake_front):.1f} psi")

                        # Key telemetry points for detailed analysis
                        context_parts.append(f"\n--- KEY TELEMETRY POINTS (every {sample_interval}th point for analysis) ---")
                        for i, point in enumerate(key_points[:50]):  # Limit to 50 points for token management
                            speed = point.get('speed', 0) or 0
                            throttle = point.get('throttle', 0) or 0
                            brake_f = point.get('brake_front', 0) or 0
                            brake_r = point.get('brake_rear', 0) or 0
                            context_parts.append(f"Point {i*sample_interval}: Speed={speed:.1f}mph, Throttle={throttle:.1f}%, BrakeF={brake_f:.1f}psi, BrakeR={brake_r:.1f}psi")

            # Best lap comparison data
            if 'best_lap' in telemetry_data:
                best_data = telemetry_data['best_lap']
                context_parts.append("\n--- BEST LAP COMPARISON ---")

                if 'lap_time' in best_data:
                    context_parts.append(f"Best Lap Time: {best_data['lap_time']}")

                if 'sector_times' in best_data:
                    for i, sector_time in enumerate(best_data['sector_times'], 1):
                        if sector_time:
                            context_parts.append(f"Best Sector {i}: {sector_time}")

                # Time delta calculation
                if 'current_lap' in telemetry_data and 'lap_time' in telemetry_data['current_lap'] and 'lap_time' in best_data:
                    try:
                        current_ms = self._parse_lap_time(telemetry_data['current_lap']['lap_time'])
                        best_ms = self._parse_lap_time(best_data['lap_time'])
                        if current_ms and best_ms:
                            delta_ms = current_ms - best_ms
                            delta_str = f"+{delta_ms/1000:.3f}s" if delta_ms > 0 else f"{delta_ms/1000:.3f}s"
                            context_parts.append(f"Time Delta: {delta_str}")
                    except Exception as e:
                        logger.warning(f"Failed to calculate time delta: {e}")

            # Track conditions or additional context
            if 'track_info' in telemetry_data:
                track_info = telemetry_data['track_info']
                context_parts.append(f"\n--- TRACK INFO ---")
                context_parts.append(f"Track: {track_info.get('name', 'Barber Motorsports Park')}")

            return '\n'.join(context_parts)

        except Exception as e:
            logger.error(f"Error preparing telemetry context: {str(e)}")
            return "Error preparing telemetry context for analysis."

    def _parse_lap_time(self, lap_time_str: str) -> Optional[int]:
        """Parse lap time string like '1:39.387' to milliseconds"""
        try:
            if ':' in lap_time_str:
                parts = lap_time_str.split(':')
                minutes = int(parts[0])
                seconds = float(parts[1])
                return int((minutes * 60 + seconds) * 1000)
            else:
                return int(float(lap_time_str) * 1000)
        except (ValueError, IndexError):
            return None

    async def analyze_racing_question(self, question: str, telemetry_context: Dict[str, Any],
                                    region: Optional[str] = None) -> Dict[str, Any]:
        """
        Send racing question with telemetry context to Claude Sonnet 4.5

        Args:
            question: User's racing question
            telemetry_context: Telemetry and lap data context
            region: Optional region override for this request

        Returns:
            Dictionary with AI response and metadata
        """
        # Update region if provided
        if region and region != self.region_name:
            self.update_region(region)

        try:
            # Prepare context
            context_str = self.prepare_telemetry_context(telemetry_context)

            # Construct the conversation
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": f"""Based on the following racing telemetry data, please answer my question:

{context_str}

QUESTION: {question}

Please provide specific, actionable advice based on the telemetry data above. Reference exact values and measurements when making recommendations."""
                        }
                    ]
                }
            ]

            # Add system message with racing expertise
            conversation_config = {
                "modelId": self.model_id,
                "messages": messages,
                "system": [{"text": self.system_prompt}],
                "inferenceConfig": {
                    "maxTokens": 2000,
                    "temperature": 0.3  # Lower temperature for consistent, factual racing advice
                }
            }

            logger.info(f"Sending request to Bedrock model {self.model_id} in region {self.region_name}")

            # Call Bedrock Converse API
            response = self.client.converse(**conversation_config)

            # Extract response
            response_text = response["output"]["message"]["content"][0]["text"]

            # Calculate tokens used
            usage = response.get("usage", {})
            input_tokens = usage.get("inputTokens", 0)
            output_tokens = usage.get("outputTokens", 0)

            return {
                "success": True,
                "response": response_text,
                "metadata": {
                    "model_id": self.model_id,
                    "region": self.region_name,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }

        except NoCredentialsError:
            logger.error("AWS credentials not found")
            return {
                "success": False,
                "error": "AWS credentials not configured. Please set up your AWS credentials.",
                "error_type": "credentials"
            }

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            logger.error(f"Bedrock API error: {error_code} - {error_message}")

            if error_code == 'AccessDeniedException':
                return {
                    "success": False,
                    "error": f"Access denied to Bedrock in region {self.region_name}. Check IAM permissions.",
                    "error_type": "access_denied"
                }
            elif error_code == 'ValidationException':
                return {
                    "success": False,
                    "error": f"Invalid request: {error_message}",
                    "error_type": "validation"
                }
            else:
                return {
                    "success": False,
                    "error": f"Bedrock error ({error_code}): {error_message}",
                    "error_type": "bedrock_error"
                }

        except Exception as e:
            logger.error(f"Unexpected error calling Bedrock: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unexpected"
            }

    def test_connection(self, region: Optional[str] = None) -> Dict[str, Any]:
        """
        Test connection to Bedrock service

        Args:
            region: Optional region to test (defaults to current region)

        Returns:
            Dictionary with connection test results
        """
        test_region = region or self.region_name

        try:
            # Create a temporary client for testing if different region
            if region and region != self.region_name:
                test_client = boto3.client("bedrock-runtime", region_name=region)
            else:
                test_client = self.client

            # Simple test message
            test_messages = [{
                "role": "user",
                "content": [{"text": "Hello, respond with 'Connection successful' if you can read this."}]
            }]

            response = test_client.converse(
                modelId=self.model_id,
                messages=test_messages,
                inferenceConfig={"maxTokens": 50, "temperature": 0.1}
            )

            return {
                "success": True,
                "message": f"Successfully connected to Bedrock in region {test_region}",
                "model_id": self.model_id,
                "region": test_region,
                "response": response["output"]["message"]["content"][0]["text"]
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to connect to Bedrock in region {test_region}",
                "error": str(e),
                "region": test_region
            }


# Global instance (will be initialized by Flask app)
racing_ai = None

def get_racing_ai(region: str = "us-west-2") -> RacingAIAssistant:
    """
    Get or create the global racing AI assistant instance

    Args:
        region: AWS region for Bedrock service

    Returns:
        RacingAIAssistant instance
    """
    global racing_ai
    if racing_ai is None or racing_ai.region_name != region:
        racing_ai = RacingAIAssistant(region_name=region)
    return racing_ai