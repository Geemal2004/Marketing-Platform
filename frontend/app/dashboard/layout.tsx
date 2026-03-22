'use client';
import DashboardNavbar from '@/components/DashboardNavbar';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const [cookie,setCookie] = useState<string[]>([]);
    const router = useRouter();
        useEffect(()=>{
             setCookie(document.cookie.split('; '));
            console.log("Cookies:", cookie);
        },[]);
       
        const userCookie = cookie.find(row => row.startsWith('user='));
        if(!userCookie){
            router.push('/login');
        }
    return (
        <div className="min-h-screen bg-[#f3f3f1] text-[#101828]">
            <DashboardNavbar />
            {children}
        </div>
    );
}
