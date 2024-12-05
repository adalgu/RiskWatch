# modules/decorators.py

import streamlit as st
import logging

def handle_exceptions(error_message):
    """예외 처리 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger('app')
                logger.error(f"{error_message}: {e}")
                st.error(error_message)
        return wrapper
    return decorator