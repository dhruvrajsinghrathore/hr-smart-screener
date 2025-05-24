import streamlit as st

st.set_page_config(layout="wide")

# Minimal hardcoded test
html = """
<style>
.custom-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 16px;
}
.custom-table th, .custom-table td {
    padding: 10px;
    border-bottom: 1px solid #444;
    text-align: left;
}
.bar-container {
    width: 100%;
    background-color: #333;
    border-radius: 4px;
    height: 8px;
}
.bar-fill {
    height: 8px;
    border-radius: 4px;
    background-color: #a855f7;
}
</style>

<table class="custom-table">
    <thead>
        <tr>
            <th>Resume</th>
            <th>Email</th>
            <th>Score</th>
            <th>Timestamp</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Dhruvraj_resume_May18.pdf</td>
            <td><a href="mailto:test@example.com" style="color:#9fbbff;">test@example.com</a></td>
            <td>
                42.59<br>
                <div class="bar-container">
                    <div class="bar-fill" style="width: 42.59%;"></div>
                </div>
            </td>
            <td>2025-05-23T18:52:49.626034</td>
        </tr>
    </tbody>
</table>
"""

st.markdown(html, unsafe_allow_html=True)
