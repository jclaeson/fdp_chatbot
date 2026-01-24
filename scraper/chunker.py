"""
Document chunker for optimizing RAG retrieval
Intelligently splits scraped content into semantically meaningful chunks
"""
import re
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    content: str
    chunk_id: str
    source_url: str
    title: str
    chunk_index: int
    metadata: Dict


class DocumentChunker:
    """Intelligent document chunking for RAG"""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 128,
        min_chunk_size: int = 100
    ):
        """
        Args:
            chunk_size: Target size for each chunk (in tokens, approximate)
            chunk_overlap: Overlap between consecutive chunks
            min_chunk_size: Minimum chunk size to avoid tiny fragments
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(self, document: Dict) -> List[Chunk]:
        """
        Chunk a scraped document into smaller pieces

        Args:
            document: Document dict from scraper

        Returns:
            List of Chunk objects
        """
        content = document.get('markdown', document.get('content', ''))
        url = document['url']
        title = document['title']

        # Try semantic chunking first (by headers, sections)
        chunks = self._semantic_chunking(content, url, title, document)

        # If semantic chunking produces too large chunks, split them further
        final_chunks = []
        for chunk in chunks:
            if self._estimate_tokens(chunk.content) > self.chunk_size * 1.5:
                # Split large chunks
                sub_chunks = self._sliding_window_chunking(
                    chunk.content, url, title, document, start_index=chunk.chunk_index
                )
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)

        return final_chunks

    def _semantic_chunking(
        self, content: str, url: str, title: str, document: Dict
    ) -> List[Chunk]:
        """Split content by semantic boundaries (headers, sections)"""
        chunks = []

        # Split by markdown headers
        sections = self._split_by_headers(content)

        for idx, section in enumerate(sections):
            if len(section.strip()) < self.min_chunk_size:
                # Merge small sections with previous chunk
                if chunks:
                    chunks[-1].content += "\n\n" + section
                continue

            chunk = Chunk(
                content=section.strip(),
                chunk_id=f"{url}#chunk-{idx}",
                source_url=url,
                title=title,
                chunk_index=idx,
                metadata={
                    **document.get('metadata', {}),
                    'chunking_method': 'semantic',
                }
            )
            chunks.append(chunk)

        return chunks if chunks else self._sliding_window_chunking(content, url, title, document)

    def _split_by_headers(self, content: str) -> List[str]:
        """Split markdown content by headers"""
        # Pattern for markdown headers
        header_pattern = r'^#{1,6}\s+.+$'

        sections = []
        current_section = []

        for line in content.split('\n'):
            if re.match(header_pattern, line):
                # Start new section
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)

        # Add last section
        if current_section:
            sections.append('\n'.join(current_section))

        return sections if sections else [content]

    def _sliding_window_chunking(
        self,
        content: str,
        url: str,
        title: str,
        document: Dict,
        start_index: int = 0
    ) -> List[Chunk]:
        """Split content using sliding window approach"""
        chunks = []

        # Split by sentences for better boundaries
        sentences = self._split_sentences(content)

        current_chunk = []
        current_length = 0
        chunk_index = start_index

        for sentence in sentences:
            sentence_length = self._estimate_tokens(sentence)

            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunk = Chunk(
                    content=chunk_text,
                    chunk_id=f"{url}#chunk-{chunk_index}",
                    source_url=url,
                    title=title,
                    chunk_index=chunk_index,
                    metadata={
                        **document.get('metadata', {}),
                        'chunking_method': 'sliding_window',
                    }
                )
                chunks.append(chunk)

                # Start new chunk with overlap
                overlap_tokens = 0
                overlap_sentences = []

                for prev_sentence in reversed(current_chunk):
                    sent_tokens = self._estimate_tokens(prev_sentence)
                    if overlap_tokens + sent_tokens <= self.chunk_overlap:
                        overlap_sentences.insert(0, prev_sentence)
                        overlap_tokens += sent_tokens
                    else:
                        break

                current_chunk = overlap_sentences
                current_length = overlap_tokens
                chunk_index += 1

            current_chunk.append(sentence)
            current_length += sentence_length

        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunk = Chunk(
                    content=chunk_text,
                    chunk_id=f"{url}#chunk-{chunk_index}",
                    source_url=url,
                    title=title,
                    chunk_index=chunk_index,
                    metadata={
                        **document.get('metadata', {}),
                        'chunking_method': 'sliding_window',
                    }
                )
                chunks.append(chunk)

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting (can be improved with spaCy/nltk)
        sentence_endings = r'[.!?]+[\s\n]+'
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate of token count"""
        # Approximate: 1 token ~= 4 characters
        return len(text) // 4

    def chunk_code_snippets(self, document: Dict) -> List[Chunk]:
        """Special handling for code snippets"""
        chunks = []
        code_snippets = document.get('code_snippets', [])

        for idx, code in enumerate(code_snippets):
            chunk = Chunk(
                content=code,
                chunk_id=f"{document['url']}#code-{idx}",
                source_url=document['url'],
                title=f"{document['title']} - Code Example {idx + 1}",
                chunk_index=idx,
                metadata={
                    **document.get('metadata', {}),
                    'content_type': 'code',
                }
            )
            chunks.append(chunk)

        return chunks


def process_scraped_data(scraped_file: str, output_file: str):
    """Process scraped JSON file and create chunked dataset"""
    import json

    # Load scraped data
    with open(scraped_file, 'r', encoding='utf-8') as f:
        documents = json.load(f)

    chunker = DocumentChunker(
        chunk_size=512,
        chunk_overlap=128,
        min_chunk_size=100
    )

    all_chunks = []

    for doc in documents:
        # Chunk main content
        content_chunks = chunker.chunk_document(doc)
        all_chunks.extend(content_chunks)

        # Chunk code snippets separately
        code_chunks = chunker.chunk_code_snippets(doc)
        all_chunks.extend(code_chunks)

    # Convert to serializable format
    chunks_dict = [
        {
            'content': chunk.content,
            'chunk_id': chunk.chunk_id,
            'source_url': chunk.source_url,
            'title': chunk.title,
            'chunk_index': chunk.chunk_index,
            'metadata': chunk.metadata,
        }
        for chunk in all_chunks
    ]

    # Save chunked data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks_dict, f, indent=2, ensure_ascii=False)

    print(f"Created {len(chunks_dict)} chunks from {len(documents)} documents")
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python chunker.py <scraped_file.json> <output_file.json>")
        sys.exit(1)

    process_scraped_data(sys.argv[1], sys.argv[2])
