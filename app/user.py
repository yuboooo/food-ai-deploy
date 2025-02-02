import streamlit as st

def show_user_profile(authenticator):
    """Display user profile in the sidebar"""
    with st.sidebar:
        # Push the profile to the bottom using an empty container
        # spacer = st.container()
        
        # Profile container at the bottom
        with st.container():
            st.markdown("### User Profile")
            if st.session_state['connected']:
                st.image(st.session_state['user_info'].get('picture'), width=100)
                st.write('Hello, '+ st.session_state['user_info'].get('name'))
                st.write('Email: '+ st.session_state['user_info'].get('email'))
                if st.button('Log out'):
                    authenticator.logout()
            else:
                authenticator.login()
                st.write("Please log in to continue.")