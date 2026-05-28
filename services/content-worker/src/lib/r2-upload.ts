/**
 * Cloudflare R2 upload via S3-compatible API.
 * Uses CF_R2_ACCOUNT_ID, CF_R2_ACCESS_KEY_ID, CF_R2_SECRET_ACCESS_KEY.
 */

import {
  S3Client,
  PutObjectCommand,
  type PutObjectCommandInput,
} from '@aws-sdk/client-s3'

const BUCKET = 'meridian-content'

function getR2Client(): S3Client {
  const accountId = process.env.CF_R2_ACCOUNT_ID ?? ''
  return new S3Client({
    region: 'auto',
    endpoint: `https://${accountId}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: process.env.CF_R2_ACCESS_KEY_ID ?? '',
      secretAccessKey: process.env.CF_R2_SECRET_ACCESS_KEY ?? '',
    },
  })
}

/**
 * Upload a buffer or stream to R2 and return the object key.
 */
export async function uploadToR2(params: {
  key: string
  body: Buffer | Uint8Array | ReadableStream
  contentType: string
}): Promise<string> {
  const client = getR2Client()

  const input: PutObjectCommandInput = {
    Bucket: BUCKET,
    Key: params.key,
    Body: params.body as PutObjectCommandInput['Body'],
    ContentType: params.contentType,
  }

  await client.send(new PutObjectCommand(input))

  return params.key
}

/**
 * Build a public download URL for an R2 object.
 * Assumes a custom domain or R2 public bucket is configured.
 */
export function downloadUrl(key: string): string {
  const accountId = process.env.CF_R2_ACCOUNT_ID ?? ''
  return `https://pub-${accountId}.r2.dev/${key}`
}
