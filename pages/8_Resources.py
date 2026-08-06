"""
Page 8: Resources.

Links to project repos, data source, and contact details.
"""
import streamlit as st

st.set_page_config(page_title="Resources", page_icon="🔗", layout="wide")

st.title("🔗 Resources")
st.warning(
    "**This is a demo project.** It uses **completely synthetic data**. "
    "It is not affiliated with, endorsed by, or connected to Ryman Healthcare "
    "(or any other organisation). Location and naming conventions are "
    "fictionalised for realism only."
)

st.divider()

st.subheader("Repositories")

st.markdown(
    """
    ### [ryman-asset-dashboard](https://github.com/lunar-me/ryman-asset-dashboard)
    This Streamlit dashboard — the analytical tool for demonstrating the work
    of an Asset Management Analyst. Includes the 7-page app, utils modules,
    and design specifications.

    ### [ryman-asset-generator](https://github.com/lunar-me/ryman-asset-generator)
    The Python script that generates the synthetic ServiceNow-style asset data
    (`ryman_assets.csv`). Customise row count, seed, and output file:
    ```bash
    python ryman_asset_generator.py --rows 20000 --seed 123 --output my_assets.csv
    ```
    """
)

st.divider()

st.subheader("Data Source")

st.markdown(
    """
    ### [ryman_assets.csv](ryman_assets.csv)
    The raw synthetic dataset (15,000 rows × 37 columns) used as the local
    fallback data source. The dashboard also supports loading the same data
    from a Supabase `ryman_assets` table.
    """
)

st.divider()

st.subheader("Contact")

st.markdown(
    """
    For questions, feedback, or collaboration enquiries:

    ✉️ **[lanarme@proton.me](mailto:lanarme@proton.me)**
    """
)