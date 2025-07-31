"""
Daily digest generation module.
Creates organized and engaging digest messages from processed Reddit posts.
"""

import logging
from datetime import datetime, timezone, date, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

from database import BotDatabase
from config import DigestConfig

logger = logging.getLogger(__name__)


@dataclass
class DigestSection:
    """Represents a section of the digest"""
    category: str
    title: str
    emoji: str
    posts: List[Dict[str, Any]]
    max_posts: int = 3


class DigestGenerator:
    """Generates organized daily digest messages"""
    
    # Category configurations with emojis and titles
    CATEGORY_CONFIG = {
        'news': DigestSection('news', 'Breaking News & Updates', '📰', [], 4),
        'tool': DigestSection('tool', 'Tools & Applications', '🛠️', [], 3),
        'research': DigestSection('research', 'Research & Papers', '🔬', [], 3),
        'tutorial': DigestSection('tutorial', 'Tutorials & Guides', '📚', [], 3),
        'discussion': DigestSection('discussion', 'Community Discussions', '💬', [], 2),
        'showcase': DigestSection('showcase', 'Projects & Demos', '🚀', [], 2),
        'question': DigestSection('question', 'Questions & Help', '❓', [], 2),
        'other': DigestSection('other', 'Other Interesting Posts', '💡', [], 2)
    }
    
    def __init__(self, database: BotDatabase, config: DigestConfig):
        self.database = database
        self.config = config
    
    async def generate_daily_digest(
        self, 
        target_date: Optional[date] = None
    ) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        Generate a comprehensive daily digest message
        
        Args:
            target_date: Date to generate digest for (default: yesterday)
        
        Returns:
            Tuple of (message_text, digest_id, post_reddit_ids)
        """
        try:
            if target_date is None:
                target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
            
            logger.info(f"Generating digest for {target_date}")
            
            # Check if digest already exists for this date
            if await self.database.check_digest_exists_for_date(target_date):
                logger.warning(f"Digest already exists for {target_date}")
                return None, None, []
            
            # Get posts by category
            posts_by_category = await self.database.get_posts_by_category(
                days_back=1,
                categories_order=self.config.categories_order
            )
            
            if not posts_by_category:
                logger.warning("No processed posts found for digest")
                return None, None, []
            
            # Create digest sections
            digest_sections = []
            total_posts = 0
            all_post_ids = []
            
            for category in self.config.categories_order:
                if category in posts_by_category and posts_by_category[category]:
                    section_config = self.CATEGORY_CONFIG.get(category)
                    if section_config:
                        posts = posts_by_category[category][:section_config.max_posts]
                        if posts:
                            section = DigestSection(
                                category=category,
                                title=section_config.title,
                                emoji=section_config.emoji,
                                posts=posts,
                                max_posts=section_config.max_posts
                            )
                            digest_sections.append(section)
                            total_posts += len(posts)
                            all_post_ids.extend([post['reddit_id'] for post in posts])
                            
                            # Stop if we've reached the max posts limit
                            if total_posts >= self.config.max_posts_per_digest:
                                break
            
            if not digest_sections:
                logger.warning("No digest sections created")
                return None, None, []
            
            # Generate the message
            message = self._format_digest_message(digest_sections, target_date, total_posts)
            
            # Create digest record
            digest_id = await self.database.create_digest_record(
                date_for_digest=target_date,
                post_count=total_posts,
                summary=f"Daily digest with {total_posts} posts across {len(digest_sections)} categories"
            )
            
            if digest_id:
                # Add posts to digest
                await self.database.add_posts_to_digest(digest_id, all_post_ids)
            
            logger.info(f"Generated digest with {total_posts} posts across {len(digest_sections)} categories")
            return message, digest_id, all_post_ids
            
        except Exception as e:
            logger.error(f"Error generating daily digest: {e}")
            return None, None, []
    
    def _format_digest_message(
        self, 
        sections: List[DigestSection], 
        target_date: date, 
        total_posts: int
    ) -> str:
        """
        Format the digest message with sections and posts
        
        Args:
            sections: List of digest sections
            target_date: Date the digest is for
            total_posts: Total number of posts included
        
        Returns:
            Formatted message string
        """
        # Header
        message_lines = [
            "🤖 **AI Daily Digest**",
            f"📅 {target_date.strftime('%B %d, %Y')}",
            f"📊 {total_posts} curated posts from AI communities",
            "",
            "🔥 **Top Stories from Reddit's AI Communities**",
            ""
        ]
        
        # Add each section
        for section in sections:
            message_lines.append(f"{section.emoji} **{section.title}**")
            message_lines.append("")
            
            for i, post in enumerate(section.posts, 1):
                # Format post entry
                post_line = self._format_post_entry(post, i)
                message_lines.append(post_line)
                message_lines.append("")
            
            message_lines.append("---")
            message_lines.append("")
        
        # Footer
        message_lines.extend([
            "💡 **Want to chat about AI?**",
            "Just send me a message - I'm powered by the same AI that creates these summaries!",
            "",
            "🔗 **Sources:** r/artificial, r/OpenAI, r/ClaudeAI, r/LocalLLaMA, r/LangChain, r/AI_Agents, r/PromptEngineering, r/singularity",
            "",
            f"⏱️ Generated at {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
        ])
        
        return "\n".join(message_lines)
    
    def _format_post_entry(self, post: Dict[str, Any], index: int) -> str:
        """
        Format a single post entry
        
        Args:
            post: Post dictionary
            index: Index number for the post
        
        Returns:
            Formatted post string
        """
        title = post.get('title', 'No title')
        summary = post.get('summary', 'No summary available')
        score = post.get('score', 0)
        subreddit = post.get('subreddit_name', 'unknown')
        url = post.get('url', '')
        permalink = post.get('permalink', '')
        
        # Truncate title if too long
        if len(title) > 100:
            title = title[:97] + "..."
        
        # Truncate summary if too long
        if len(summary) > 200:
            summary = summary[:197] + "..."
        
        # Create post entry
        post_lines = [
            f"**{index}. {title}**",
            f"📈 {score} upvotes • r/{subreddit}",
            f"💬 {summary}"
        ]
        
        # Add link if available
        if url and url != permalink:
            post_lines.append(f"🔗 [Read more]({url})")
        elif permalink:
            post_lines.append(f"🔗 [Discussion]({permalink})")
        
        return "\n".join(post_lines)
    
    async def generate_stats_message(self) -> str:
        """
        Generate a statistics message about the content processing
        
        Returns:
            Formatted statistics message
        """
        try:
            stats = await self.database.get_processing_stats()
            recent_digests = await self.database.get_recent_digests(limit=7)
            
            message_lines = [
                "📊 **AI Daily Digest Statistics**",
                "",
                f"📝 **Content Processing:**",
                f"• Total posts: {stats.get('total_posts', 0):,}",
                f"• Processed posts: {stats.get('processed_posts', 0):,}",
                f"• Processing rate: {stats.get('processing_rate', 0)}%",
                "",
                "📂 **Posts by Category:**"
            ]
            
            # Add category breakdown
            category_breakdown = stats.get('category_breakdown', {})
            for category, count in sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True):
                emoji = self.CATEGORY_CONFIG.get(category, {}).get('emoji', '📄')
                title = self.CATEGORY_CONFIG.get(category, {}).get('title', category.title())
                message_lines.append(f"• {emoji} {title}: {count:,}")
            
            message_lines.extend([
                "",
                f"📅 **Recent Digests:** {len(recent_digests)} in last 7 days"
            ])
            
            # Add recent digest info
            for digest in recent_digests[:3]:
                digest_date = digest.get('date', 'Unknown')
                post_count = digest.get('post_count', 0)
                status = digest.get('status', 'unknown')
                status_emoji = '✅' if status == 'completed' else '⏳' if status == 'pending' else '❌'
                message_lines.append(f"• {status_emoji} {digest_date}: {post_count} posts")
            
            message_lines.extend([
                "",
                f"⏱️ Updated at {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
            ])
            
            return "\n".join(message_lines)
            
        except Exception as e:
            logger.error(f"Error generating stats message: {e}")
            return "❌ Unable to generate statistics at this time."