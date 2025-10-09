"""Task templates for common CrewAI use cases."""

from typing import List, Dict, Any


class TaskTemplates:
    """Common task templates based on CrewAI patterns."""

    @staticmethod
    def research_task() -> Dict[str, Any]:
        """Research and information gathering task."""
        return {
            "name": "Research Task",
            "description": """Conduct thorough research on the given topic.
Use available tools to search for information, gather data from multiple sources,
and compile comprehensive findings. Focus on accuracy and relevance.""",
            "expected_output": """A detailed research report containing:
- Key findings and insights
- Data from multiple reliable sources
- Summary of main points
- References and citations""",
            "order": 0,
            "async_execution": False,
            "output_format": "text",
        }

    @staticmethod
    def analysis_task() -> Dict[str, Any]:
        """Data analysis and interpretation task."""
        return {
            "name": "Analysis Task",
            "description": """Analyze the provided data or research findings.
Identify patterns, trends, and insights. Apply critical thinking to draw meaningful conclusions.
Use analytical tools if available.""",
            "expected_output": """A comprehensive analysis report including:
- Data patterns and trends
- Key insights and observations
- Statistical findings (if applicable)
- Recommendations based on analysis""",
            "order": 1,
            "async_execution": False,
            "output_format": "text",
        }

    @staticmethod
    def writing_task() -> Dict[str, Any]:
        """Content creation and writing task."""
        return {
            "name": "Writing Task",
            "description": """Create high-quality written content based on the research and analysis.
Ensure the content is well-structured, engaging, and meets the specified requirements.
Use proper formatting and tone appropriate for the target audience.""",
            "expected_output": """A polished written piece that includes:
- Clear introduction and conclusion
- Well-organized body content
- Proper formatting and structure
- Engaging and accessible language""",
            "order": 2,
            "async_execution": False,
            "output_format": "text",
        }

    @staticmethod
    def code_generation_task() -> Dict[str, Any]:
        """Code development task."""
        return {
            "name": "Code Generation Task",
            "description": """Write clean, efficient, and well-documented code to solve the given problem.
Follow best practices and coding standards. Include error handling and edge cases.
Add comments to explain complex logic.""",
            "expected_output": """Working code that includes:
- Clean, readable implementation
- Proper error handling
- Documentation and comments
- Test cases (if applicable)""",
            "order": 0,
            "async_execution": False,
            "output_format": "text",
        }

    @staticmethod
    def review_task() -> Dict[str, Any]:
        """Review and quality assurance task."""
        return {
            "name": "Review Task",
            "description": """Review the previous work for quality, accuracy, and completeness.
Identify any issues, errors, or areas for improvement. Provide constructive feedback
and suggestions for enhancement.""",
            "expected_output": """A detailed review report containing:
- Quality assessment
- List of identified issues
- Suggestions for improvement
- Overall evaluation and rating""",
            "order": 3,
            "async_execution": False,
            "output_format": "text",
        }

    @staticmethod
    def planning_task() -> Dict[str, Any]:
        """Planning and strategy task."""
        return {
            "name": "Planning Task",
            "description": """Develop a comprehensive plan or strategy for the given objective.
Break down the goal into actionable steps, identify resources needed, and establish
timelines. Consider potential challenges and mitigation strategies.""",
            "expected_output": """A detailed plan including:
- Clear objectives and goals
- Step-by-step action items
- Timeline and milestones
- Resource requirements
- Risk assessment and mitigation""",
            "order": 0,
            "async_execution": False,
            "output_format": "text",
        }

    @staticmethod
    def data_extraction_task() -> Dict[str, Any]:
        """Data extraction and processing task."""
        return {
            "name": "Data Extraction Task",
            "description": """Extract relevant data from specified sources using available tools.
Clean and structure the data for further processing. Ensure data quality and consistency.""",
            "expected_output": """Extracted and structured data in the format:
- Clean, validated data
- Proper data structure
- Summary of data collected
- Data quality report""",
            "order": 0,
            "async_execution": False,
            "output_format": "json",
        }

    @staticmethod
    def summarization_task() -> Dict[str, Any]:
        """Content summarization task."""
        return {
            "name": "Summarization Task",
            "description": """Summarize the provided content or research findings into a concise format.
Capture key points and main ideas while maintaining accuracy. Make it accessible
and easy to understand.""",
            "expected_output": """A concise summary that includes:
- Executive summary (1-2 paragraphs)
- Key points and takeaways
- Main conclusions
- Action items (if applicable)""",
            "order": 4,
            "async_execution": False,
            "output_format": "text",
        }

    @staticmethod
    def get_all_templates() -> List[Dict[str, Any]]:
        """Get all available task templates."""
        return [
            TaskTemplates.research_task(),
            TaskTemplates.analysis_task(),
            TaskTemplates.writing_task(),
            TaskTemplates.code_generation_task(),
            TaskTemplates.review_task(),
            TaskTemplates.planning_task(),
            TaskTemplates.data_extraction_task(),
            TaskTemplates.summarization_task(),
        ]

    @staticmethod
    def get_workflow_templates() -> Dict[str, List[Dict[str, Any]]]:
        """Get pre-configured workflow templates (multiple tasks working together)."""
        return {
            "research_and_report": [
                TaskTemplates.research_task(),
                TaskTemplates.analysis_task(),
                TaskTemplates.writing_task(),
                TaskTemplates.review_task(),
                TaskTemplates.summarization_task(),
            ],
            "code_development": [
                TaskTemplates.planning_task(),
                TaskTemplates.code_generation_task(),
                TaskTemplates.review_task(),
            ],
            "data_pipeline": [
                TaskTemplates.data_extraction_task(),
                TaskTemplates.analysis_task(),
                TaskTemplates.summarization_task(),
            ],
            "content_creation": [
                TaskTemplates.research_task(),
                TaskTemplates.writing_task(),
                TaskTemplates.review_task(),
            ],
        }
