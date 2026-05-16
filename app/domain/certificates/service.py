def resolve_certificate_asset(cert_type):
    from app.models import db, CertificateAsset
    if cert_type.asset_id:
        asset = db.session.get(CertificateAsset, cert_type.asset_id)
        if asset and asset.file_binary:
            return asset.file_binary

    raise RuntimeError("CERT_ASSET_MISSING")

