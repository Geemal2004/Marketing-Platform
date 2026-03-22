import DashboardNavbar from '@/components/DashboardNavbar';

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="min-h-screen bg-[#f3f3f1] text-[#101828]">
            <DashboardNavbar />
            {children}
        </div>
    );
}
