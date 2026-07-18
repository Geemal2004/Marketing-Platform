'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { billingApi } from '@/lib/api';
import { Loader2 } from 'lucide-react';

const FALLBACK = {
    payments_enabled: false,
    message: 'Payments are not enabled yet. This describes the planned revenue model.',
    plans: [
        { tier: 'FREE', monthly_credits: 200, max_agents: 50, max_days: 7, max_video_seconds: 300 },
        { tier: 'PRO', monthly_credits: 1000, max_agents: 500, max_days: 14, max_video_seconds: 900 },
        { tier: 'ENTERPRISE', monthly_credits: 5000, max_agents: 5000, max_days: 30, max_video_seconds: 1800 },
    ],
    pricing: {
        signup_grant_free: 200,
        vlm_text_paste: 0,
        vlm_text_file: 5,
        vlm_image_or_audio: 15,
        vlm_video: '20 + 2 credits per 15 seconds of video',
        simulation: '1 credit × number of agents × simulation days',
    },
    examples: [
        { label: 'Small free-tier run', detail: '10 agents × 5 days = 50 credits', simulation_credits: 50 },
        { label: 'Typical image campaign', detail: 'Image VLM + 50 agents × 7 days', vlm_credits: 15, simulation_credits: 350 },
        { label: '60-second video', detail: 'Video analysis cost only', vlm_credits: 28 },
    ],
};

export default function BillingPage() {
    const { data, isLoading } = useQuery({
        queryKey: ['billing', 'plans'],
        queryFn: billingApi.plans,
        retry: 1,
    });

    const info = data || FALLBACK;

    if (isLoading && !data) {
        return (
            <div className="flex h-[calc(100vh-64px)] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-[#00897f]" />
            </div>
        );
    }

    return (
        <div className="bg-[#f3f3f1] text-[#101828] min-h-[calc(100vh-64px)]">
            <main className="mx-auto max-w-[1100px] px-6 py-10">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold tracking-tight">Pricing & revenue model</h1>
                    <p className="mt-2 text-[#4b5563] max-w-2xl">
                        {info.message}
                    </p>
                    <p className="mt-2 inline-block rounded-md bg-[#fef3c7] border border-[#fde68a] px-3 py-1.5 text-sm text-[#92400e]">
                        Payments are not charged yet — this page is informational only.
                    </p>
                </div>

                <div className="rounded-xl border border-[#e5e7eb] bg-white p-6 mb-8">
                    <h2 className="text-lg font-semibold mb-4">Planned plans</h2>
                    <div className="grid gap-4 sm:grid-cols-3">
                        {(info.plans || []).map((plan: any) => (
                            <div key={plan.tier} className="rounded-lg border border-[#e5e7eb] bg-[#fafafa] p-4">
                                <p className="font-semibold">{plan.tier}</p>
                                <p className="mt-1 text-2xl font-bold">{plan.monthly_credits}</p>
                                <p className="text-xs text-[#6b7280]">credits / month (planned)</p>
                                <ul className="mt-3 space-y-1 text-xs text-[#4b5563]">
                                    <li>Up to {plan.max_agents} agents</li>
                                    <li>Up to {plan.max_days} simulation days</li>
                                    <li>Videos up to {Math.floor(plan.max_video_seconds / 60)} min</li>
                                </ul>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="grid gap-6 md:grid-cols-2 mb-8">
                    <div className="rounded-xl border border-[#e5e7eb] bg-white p-6">
                        <h2 className="text-lg font-semibold mb-3">How credits will be spent</h2>
                        <ul className="text-sm text-[#4b5563] space-y-2 list-disc pl-5">
                            <li>
                                New FREE users: <strong>{info.pricing?.signup_grant_free ?? 200}</strong> starter credits
                            </li>
                            <li>Paste-only text projects: free ({info.pricing?.vlm_text_paste ?? 0} credits)</li>
                            <li>Text file analysis: {info.pricing?.vlm_text_file ?? 5} credits</li>
                            <li>Image / audio analysis: {info.pricing?.vlm_image_or_audio ?? 15} credits</li>
                            <li>Video analysis: {info.pricing?.vlm_video}</li>
                            <li>Simulation: {info.pricing?.simulation}</li>
                        </ul>
                    </div>

                    <div className="rounded-xl border border-[#e5e7eb] bg-white p-6">
                        <h2 className="text-lg font-semibold mb-3">Example costs</h2>
                        <ul className="space-y-3 text-sm">
                            {(info.examples || []).map((ex: any) => (
                                <li key={ex.label} className="border-b border-[#f3f4f6] pb-3 last:border-0">
                                    <p className="font-medium text-[#111827]">{ex.label}</p>
                                    <p className="text-[#6b7280]">{ex.detail}</p>
                                    <p className="mt-1 text-[#00897f] font-medium">
                                        {ex.vlm_credits != null && <>VLM {ex.vlm_credits} · </>}
                                        {ex.simulation_credits != null && <>Sim {ex.simulation_credits} credits</>}
                                        {ex.vlm_credits != null && ex.simulation_credits == null && <>credits</>}
                                    </p>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                <div className="rounded-xl border border-[#e5e7eb] bg-white p-6">
                    <h2 className="text-lg font-semibold mb-2">Revenue flow (planned)</h2>
                    <ol className="list-decimal pl-5 text-sm text-[#4b5563] space-y-2">
                        <li>User signs up → receives free starter credits on the FREE plan.</li>
                        <li>Uploading media spends credits for AI decomposition (by type / video length).</li>
                        <li>Starting a simulation spends credits by agent count × days.</li>
                        <li>Monthly membership grants more credits; optional top-up packs later.</li>
                        <li>Stripe checkout will plug in later — metering is not active in the app today.</li>
                    </ol>
                    <p className="mt-4 text-sm">
                        <Link href="/dashboard/new" className="text-[#00897f] font-medium hover:underline">
                            Create a project
                        </Link>
                        {' · '}
                        <Link href="/dashboard" className="text-[#00897f] font-medium hover:underline">
                            View projects
                        </Link>
                    </p>
                </div>
            </main>
        </div>
    );
}
