"""Property test fixtures and strategies for all-memos summary tests."""

from datetime import datetime, timezone, timedelta
from hypothesis import strategies as st

from src.models.memo import Memo


# Strategy for generating valid memo IDs (UUIDs as strings)
memo_id_strategy = st.uuids().map(str)


# Strategy for generating valid memo titles (1-200 characters)
memo_title_strategy = st.text(
    min_size=1,
    max_size=200,
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
        whitelist_characters='あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん日本語テスト'
    )
)


# Strategy for generating valid memo content (1-50000 characters)
memo_content_strategy = st.text(
    min_size=1,
    max_size=50000,
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Po'),
        whitelist_characters='あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん日本語テスト。、'
    )
)


# Strategy for generating short memo content (for testing aggregation limits)
short_content_strategy = st.text(
    min_size=10,
    max_size=1000,
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))
)


# Strategy for generating timestamps (naive datetimes, will add UTC timezone)
timestamp_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2025, 12, 31)
).map(lambda dt: dt.replace(tzinfo=timezone.utc))


# Strategy for generating Memo objects
@st.composite
def memo_strategy(draw, content_strategy=memo_content_strategy):
    """
    Generate a valid Memo object.
    
    Args:
        draw: Hypothesis draw function
        content_strategy: Strategy for generating content
        
    Returns:
        Memo object with random valid data
    """
    memo_id = draw(memo_id_strategy)
    title = draw(memo_title_strategy)
    content = draw(content_strategy)
    created_at = draw(timestamp_strategy)
    
    # updated_at must be >= created_at (remove timezone for strategy, add back after)
    created_at_naive = created_at.replace(tzinfo=None)
    updated_at_naive = draw(st.datetimes(
        min_value=created_at_naive,
        max_value=created_at_naive + timedelta(days=365)
    ))
    updated_at = updated_at_naive.replace(tzinfo=timezone.utc)
    
    return Memo(
        id=memo_id,
        title=title,
        content=content,
        created_at=created_at,
        updated_at=updated_at
    )


# Strategy for generating lists of memos
memo_list_strategy = st.lists(
    memo_strategy(),
    min_size=0,
    max_size=100
)


# Strategy for generating lists of memos with short content (for aggregation testing)
short_memo_list_strategy = st.lists(
    memo_strategy(content_strategy=short_content_strategy),
    min_size=1,
    max_size=50
)


# Strategy for generating Japanese text
japanese_text_strategy = st.text(
    min_size=1,
    max_size=1000,
    alphabet=st.characters(
        whitelist_characters='あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん日本語テスト。、'
    )
)


# Strategy for generating error types
error_type_strategy = st.sampled_from([
    'ValidationError',
    'ServiceUnavailable',
    'InternalError',
    'ThrottlingException'
])


# Strategy for generating HTTP status codes
status_code_strategy = st.sampled_from([200, 400, 500, 503, 504])


# Strategy for generating request IDs
request_id_strategy = st.uuids().map(str)
