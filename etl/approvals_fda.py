def upsert_approvals(approvals, conn):
    """Upsert approvals into database (insert even if no drug match)."""
    logger.info("Processing FDA approvals...")
    
    with conn.cursor() as cur:
        processed = 0
        
        for approval in approvals:
            try:
                # Extract drug information
                openfda = approval.get('openfda', {})
                brand_names = openfda.get('brand_name', [])
                generic_names = openfda.get('generic_name', [])
                
                # Use first available name
                drug_name = None
                if brand_names:
                    drug_name = brand_names[0]
                elif generic_names:
                    drug_name = generic_names[0]
                
                # Match to existing drug (if possible)
                drug_id = None
                if drug_name:
                    drug_id = fuzzy_match_drug(drug_name, conn)
                
                # Process submissions
                submissions = approval.get('submissions', [])
                for submission in submissions:
                    submission_date = submission.get('submission_date')
                    if not submission_date:
                        continue
                    
                    try:
                        approval_date = datetime.strptime(submission_date, '%Y%m%d').date()
                    except:
                        continue
                    
                    application_docs = submission.get('application_docs', [])
                    for doc in application_docs:
                        doc_url = doc.get('url', '')
                        doc_type = doc.get('type', '')
                        
                        if 'approval' in doc_type.lower():
                            # Insert approval record, even if drug_id is NULL
                            cur.execute("""
                                INSERT INTO public.approvals 
                                (agency, approval_date, drug_id, document_url, application_number, created_at)
                                VALUES (%s, %s, %s, %s, %s, NOW())
                                ON CONFLICT DO NOTHING
                            """, (
                                'FDA',
                                approval_date,
                                drug_id,  # may be NULL
                                doc_url,
                                approval.get('application_number', '')
                            ))
                            processed += 1
                            break
                
            except Exception as e:
                logger.warning(f"Error processing approval record: {str(e)}")
                continue
        
        conn.commit()
        logger.info(f"Processed {processed} FDA approval records (with NULL drug_id if no match).")
